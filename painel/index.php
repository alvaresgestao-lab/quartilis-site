<?php
// Painel Quartilis: publicação de artigos do Blog e do site de Serenatas.
// Salva o conteúdo no repositório GitHub; o site é republicado automaticamente.
session_start();
$CFG = @include __DIR__ . '/config.php';
if (!$CFG) { die('Painel ainda não configurado (config.php ausente).'); }

$SITES = [
  'blog' => [
    'label' => 'Blog Quartilis', 'json' => 'content/blog-conteudo.json',
    'url' => 'https://blog.quartilis.com.br', 'permalink' => 'data',
    'uploads' => 'blog.quartilis.com.br/uploads',
  ],
  'serenata' => [
    'label' => 'Blog de Serenatas', 'json' => 'content/serenata-conteudo.json',
    'url' => 'https://serenata.quartilis.com.br', 'permalink' => 'simples',
    'uploads' => 'serenata.quartilis.com.br/uploads',
  ],
];

// ---------- helpers GitHub ----------
function gh($method, $path, $body = null) {
  global $CFG;
  $ch = curl_init("https://api.github.com/repos/{$CFG['repo']}/$path");
  $hdr = ['User-Agent: PainelQuartilis', 'Accept: application/vnd.github+json',
          'Authorization: Bearer ' . $CFG['github_token']];
  if ($body !== null) { $hdr[] = 'Content-Type: application/json'; }
  curl_setopt_array($ch, [CURLOPT_CUSTOMREQUEST => $method, CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => $hdr, CURLOPT_TIMEOUT => 60]);
  if ($body !== null) curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body));
  $res = curl_exec($ch);
  $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
  curl_close($ch);
  return [$code, json_decode($res, true)];
}
function gh_read($path) {
  list($code, $r) = gh('GET', "contents/$path?ref=main");
  if ($code !== 200) return [null, null];
  return [base64_decode($r['content']), $r['sha']];
}
function gh_write($path, $content, $msg, $sha = null) {
  $body = ['message' => $msg, 'content' => base64_encode($content), 'branch' => 'main'];
  if ($sha) $body['sha'] = $sha;
  list($code, $r) = gh('PUT', "contents/$path", $body);
  return $code === 200 || $code === 201;
}

// ---------- helpers ----------
function slugify($t) {
  $t = mb_strtolower(trim($t));
  $t = strtr($t, ['á'=>'a','à'=>'a','ã'=>'a','â'=>'a','é'=>'e','ê'=>'e','í'=>'i','ó'=>'o','ô'=>'o','õ'=>'o','ú'=>'u','ü'=>'u','ç'=>'c','ñ'=>'n']);
  $t = preg_replace('/[^a-z0-9]+/', '-', $t);
  return trim(preg_replace('/-+/', '-', $t), '-');
}
function e($s) { return htmlspecialchars($s ?? '', ENT_QUOTES, 'UTF-8'); }
function url_post($site, $p) {
  global $SITES;
  if ($SITES[$site]['permalink'] === 'data') {
    $d = substr($p['post_date'], 0, 10);
    return $SITES[$site]['url'] . '/' . str_replace('-', '/', $d) . '/' . $p['post_name'] . '/';
  }
  return $SITES[$site]['url'] . '/' . $p['post_name'] . '/';
}
function redimensionar($tmp, $mime) {
  // reduz a foto para no máximo 1600px (JPEG) para o site carregar rápido
  if (!function_exists('imagecreatefromjpeg')) return file_get_contents($tmp);
  $img = @($mime === 'image/png' ? imagecreatefrompng($tmp) : imagecreatefromjpeg($tmp));
  if (!$img) return file_get_contents($tmp);
  $w = imagesx($img); $h = imagesy($img);
  $max = 1600; $esc = min(1, $max / max($w, $h));
  $nw = (int)($w * $esc); $nh = (int)($h * $esc);
  $novo = imagecreatetruecolor($nw, $nh);
  imagecopyresampled($novo, $img, 0, 0, 0, 0, $nw, $nh, $w, $h);
  ob_start(); imagejpeg($novo, null, 82); $out = ob_get_clean();
  imagedestroy($img); imagedestroy($novo);
  return $out;
}

// ---------- login ----------
if (isset($_GET['sair'])) { session_destroy(); header('Location: ./'); exit; }
if (isset($_POST['senha'])) {
  sleep(1); // freio contra tentativas em sequência
  if (password_verify($_POST['senha'], $CFG['senha_hash'])) {
    $_SESSION['ok'] = true; $_SESSION['csrf'] = bin2hex(random_bytes(16));
    header('Location: ./'); exit;
  }
  $erro_login = 'Senha incorreta. Tente novamente.';
}
$logada = !empty($_SESSION['ok']);

// ---------- ações (logada) ----------
$msg_ok = null; $msg_erro = null;
if ($logada && $_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['acao'])) {
  if (($_POST['csrf'] ?? '') !== ($_SESSION['csrf'] ?? '-')) { die('Sessão expirada. Volte e tente de novo.'); }
  $site = $_POST['site'] ?? 'blog';
  if (!isset($SITES[$site])) die('site inválido');
  list($json_raw, $sha) = gh_read($SITES[$site]['json']);
  $posts = $json_raw ? json_decode($json_raw, true) : null;
  if (!is_array($posts)) { $msg_erro = 'Não consegui ler o conteúdo atual. Tente de novo em instantes.'; }
  else if ($_POST['acao'] === 'salvar') {
    $titulo = trim($_POST['titulo'] ?? '');
    $texto  = trim($_POST['texto'] ?? '');
    $data   = $_POST['data'] ?: date('Y-m-d');
    $slug_orig = $_POST['slug_original'] ?? '';
    if ($titulo === '' || $texto === '') { $msg_erro = 'Preencha o título e o texto.'; }
    else {
      // fotos enviadas: sobem pro repositório e entram no fim do artigo
      $imgs_html = '';
      if (!empty($_FILES['fotos']['name'][0])) {
        foreach ($_FILES['fotos']['name'] as $i => $nome_arq) {
          if ($_FILES['fotos']['error'][$i] !== UPLOAD_ERR_OK) continue;
          $mime = mime_content_type($_FILES['fotos']['tmp_name'][$i]);
          if (!in_array($mime, ['image/jpeg', 'image/png'])) continue;
          $bin = redimensionar($_FILES['fotos']['tmp_name'][$i], $mime);
          $nome_final = date('Ymd-His') . "-$i-" . slugify(pathinfo($nome_arq, PATHINFO_FILENAME)) . '.jpg';
          if (gh_write($SITES[$site]['uploads'] . "/$nome_final", $bin, "painel: foto $nome_final")) {
            $imgs_html .= "\n\n<img src=\"uploads/$nome_final\" alt=\"\">";
          }
        }
      }
      $slug = $slug_orig !== '' ? $slug_orig : slugify($titulo);
      // remove versão anterior (edição) e garante slug único (novo)
      if ($slug_orig !== '') {
        $posts = array_values(array_filter($posts, fn($p) => $p['post_name'] !== $slug_orig || $p['post_type'] !== 'post'));
      } else {
        $base = $slug; $n = 2;
        while (array_filter($posts, fn($p) => $p['post_name'] === $slug)) { $slug = "$base-$n"; $n++; }
      }
      $posts[] = [
        'ID' => (string)time(), 'post_author' => '1',
        'post_date' => "$data " . date('H:i:s'), 'post_date_gmt' => "$data " . date('H:i:s'),
        'post_content' => $texto . $imgs_html, 'post_title' => $titulo, 'post_excerpt' => '',
        'post_status' => 'publish', 'comment_status' => 'closed', 'ping_status' => 'closed',
        'post_password' => '', 'post_name' => $slug, 'to_ping' => '', 'pinged' => '',
        'post_modified' => date('Y-m-d H:i:s'), 'post_modified_gmt' => date('Y-m-d H:i:s'),
        'post_content_filtered' => '', 'post_parent' => '0', 'guid' => '', 'menu_order' => '0',
        'post_type' => 'post', 'post_mime_type' => '', 'comment_count' => '0',
      ];
      $novo_json = json_encode($posts, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
      if (gh_write($SITES[$site]['json'], $novo_json, "painel: artigo '$titulo' ({$SITES[$site]['label']})", $sha)) {
        $msg_ok = $titulo;
      } else { $msg_erro = 'Falha ao salvar. Tente de novo em instantes.'; }
    }
  }
  else if ($_POST['acao'] === 'excluir') {
    $slug = $_POST['slug'] ?? '';
    $antes = count($posts);
    $posts = array_values(array_filter($posts, fn($p) => !($p['post_name'] === $slug && $p['post_type'] === 'post')));
    if (count($posts) < $antes) {
      $novo_json = json_encode($posts, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
      if (gh_write($SITES[$site]['json'], $novo_json, "painel: exclui artigo '$slug' ({$SITES[$site]['label']})", $sha)) {
        $msg_ok = '__excluido__';
      } else { $msg_erro = 'Falha ao excluir. Tente de novo.'; }
    }
  }
}

// ---------- dados para as telas ----------
$site_atual = $_GET['site'] ?? $_POST['site'] ?? 'blog';
if (!isset($SITES[$site_atual])) $site_atual = 'blog';
$lista = []; $editando = null;
if ($logada && !isset($_GET['novo']) && !isset($_GET['editar'])) {
  list($json_raw, ) = gh_read($SITES[$site_atual]['json']);
  $todos = $json_raw ? (json_decode($json_raw, true) ?: []) : [];
  $lista = array_values(array_filter($todos, fn($p) => $p['post_type'] === 'post'));
  usort($lista, fn($a, $b) => strcmp($b['post_date'], $a['post_date']));
}
if ($logada && isset($_GET['editar'])) {
  list($json_raw, ) = gh_read($SITES[$site_atual]['json']);
  $todos = $json_raw ? (json_decode($json_raw, true) ?: []) : [];
  foreach ($todos as $p) { if ($p['post_name'] === $_GET['editar'] && $p['post_type'] === 'post') { $editando = $p; break; } }
}
?><!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Painel Quartilis</title>
<link rel="icon" type="image/png" href="../assets/favicon.png">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600&family=Jost:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root{--creme:#dfddd0;--creme2:#f4f2e2;--sage:#8f8c74;--ink:#2b2a24;--ok:#2e7d32;--err:#b3261e}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Jost',sans-serif;font-weight:300;background:var(--creme2);color:var(--ink);min-height:100vh}
.caixa{max-width:720px;margin:0 auto;padding:30px 16px 60px}
h1{font-family:'Cormorant Garamond',serif;font-size:30px;margin-bottom:4px}
h2{font-family:'Cormorant Garamond',serif;font-size:24px;margin:22px 0 10px}
.cartao{background:#fff;border:1px solid var(--creme);padding:26px;margin-top:18px}
label{display:block;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--sage);margin:16px 0 5px}
input[type=text],input[type=date],input[type=password],textarea,select{width:100%;padding:12px;border:1px solid var(--creme);background:var(--creme2);font:inherit;font-size:16px}
textarea{min-height:280px;line-height:1.6}
.btn{display:inline-block;background:var(--ink);color:#fff;border:1px solid var(--ink);padding:13px 26px;font:inherit;font-size:13px;letter-spacing:.12em;text-transform:uppercase;cursor:pointer;text-decoration:none;margin-top:18px}
.btn:hover{background:transparent;color:var(--ink)}
.btn-claro{background:transparent;color:var(--ink)}
.aviso{background:#fdf6e3;border-left:4px solid #d4a017;padding:12px 14px;font-size:14px;margin-top:16px;line-height:1.5}
.ok{background:#e8f5e9;border-left:4px solid var(--ok);padding:14px;margin-top:16px;line-height:1.5}
.erro{background:#fdecea;border-left:4px solid var(--err);padding:14px;margin-top:16px}
.topo-painel{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
.abas{display:flex;gap:8px;margin-top:18px}
.abas a{padding:10px 18px;text-decoration:none;color:var(--ink);border:1px solid var(--creme);background:#fff;font-size:14px;letter-spacing:.06em;text-transform:uppercase}
.abas a.ativa{background:var(--ink);color:#fff;border-color:var(--ink)}
.post{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:13px 0;border-bottom:1px solid var(--creme2);flex-wrap:wrap}
.post small{color:var(--sage);display:block}
.post .acoes{display:flex;gap:14px;font-size:13px}
.post .acoes a,.post .acoes button{color:var(--sage);text-decoration:underline;background:none;border:0;cursor:pointer;font:inherit;font-size:13px}
.dica{font-size:13px;color:var(--sage);margin-top:4px;line-height:1.5}
.sair{font-size:13px;color:var(--sage);text-decoration:underline}
</style>
</head>
<body>
<div class="caixa">
<?php if (!$logada): ?>
  <div class="cartao" style="max-width:420px;margin:12vh auto 0;text-align:center">
    <h1>Painel Quartilis</h1>
    <p class="dica">Área da Ana Paula para publicar artigos no blog e no site de Serenatas.</p>
    <?php if (!empty($erro_login)): ?><div class="erro"><?= e($erro_login) ?></div><?php endif; ?>
    <form method="post">
      <label for="senha">Senha</label>
      <input id="senha" type="password" name="senha" autofocus>
      <button class="btn" type="submit">Entrar</button>
    </form>
  </div>
<?php else: ?>
  <div class="topo-painel">
    <div><h1>Painel Quartilis</h1>
    <p class="dica">Olá, Ana! Aqui você publica, edita e exclui os artigos.</p></div>
    <a class="sair" href="?sair=1">Sair</a>
  </div>
  <div class="aviso">⏱ <strong>Importante:</strong> depois de publicar, editar ou excluir, o site é atualizado automaticamente. Isso leva <strong>alguns minutos</strong> (normalmente até 10). Não precisa publicar de novo: é só aguardar e recarregar a página do blog.</div>

  <?php if ($msg_ok === '__excluido__'): ?>
    <div class="ok">🗑 Artigo excluído. A alteração entra no ar em alguns minutos.</div>
  <?php elseif ($msg_ok): ?>
    <div class="ok">✅ <strong>"<?= e($msg_ok) ?>" foi enviado com sucesso!</strong><br>O artigo entra no ar em alguns minutos (normalmente até 10), no endereço do <?= e($SITES[$site_atual]['label']) ?>.</div>
  <?php elseif ($msg_erro): ?>
    <div class="erro"><?= e($msg_erro) ?></div>
  <?php endif; ?>

  <div class="abas">
    <?php foreach ($SITES as $k => $sdef): ?>
      <a href="?site=<?= $k ?>" class="<?= $k === $site_atual ? 'ativa' : '' ?>"><?= e($sdef['label']) ?></a>
    <?php endforeach; ?>
  </div>

  <?php if ($editando || isset($_GET['novo'])): ?>
  <div class="cartao">
    <h2><?= $editando ? 'Editar artigo' : 'Novo artigo' ?> · <?= e($SITES[$site_atual]['label']) ?></h2>
    <form method="post" enctype="multipart/form-data">
      <input type="hidden" name="acao" value="salvar">
      <input type="hidden" name="csrf" value="<?= e($_SESSION['csrf']) ?>">
      <input type="hidden" name="site" value="<?= e($site_atual) ?>">
      <input type="hidden" name="slug_original" value="<?= e($editando['post_name'] ?? '') ?>">
      <label for="titulo">Título</label>
      <input id="titulo" type="text" name="titulo" value="<?= e($editando['post_title'] ?? '') ?>" required>
      <label for="data">Data</label>
      <input id="data" type="date" name="data" value="<?= e(substr($editando['post_date'] ?? date('Y-m-d'), 0, 10)) ?>">
      <label for="texto">Texto</label>
      <textarea id="texto" name="texto" required><?= e($editando['post_content'] ?? '') ?></textarea>
      <p class="dica">Dicas: deixe uma linha em branco entre os parágrafos. Pra incluir um vídeo, cole o link do YouTube sozinho numa linha, que ele vira um player automaticamente.</p>
      <label for="fotos">Fotos (opcional, entram no fim do artigo)</label>
      <input id="fotos" type="file" name="fotos[]" accept="image/jpeg,image/png" multiple>
      <button class="btn" type="submit">Publicar</button>
      <a class="btn btn-claro" href="?site=<?= e($site_atual) ?>">Cancelar</a>
    </form>
  </div>
  <?php else: ?>
  <div class="cartao">
    <div class="topo-painel">
      <h2 style="margin-top:0">Artigos publicados</h2>
      <a class="btn" style="margin-top:0" href="?site=<?= e($site_atual) ?>&novo=1">+ Novo artigo</a>
    </div>
    <?php if (!$lista): ?><p class="dica" style="margin-top:14px">Nenhum artigo carregado (ou falha temporária ao ler). Recarregue a página.</p><?php endif; ?>
    <?php foreach ($lista as $p): ?>
      <div class="post">
        <div><strong><?= e($p['post_title']) ?></strong><small><?= e(substr($p['post_date'], 0, 10)) ?></small></div>
        <div class="acoes">
          <a href="<?= e(url_post($site_atual, $p)) ?>" target="_blank">ver</a>
          <a href="?site=<?= e($site_atual) ?>&editar=<?= e($p['post_name']) ?>">editar</a>
          <form method="post" onsubmit="return confirm('Excluir o artigo &quot;<?= e($p['post_title']) ?>&quot;? Essa ação não pode ser desfeita.')" style="display:inline">
            <input type="hidden" name="acao" value="excluir">
            <input type="hidden" name="csrf" value="<?= e($_SESSION['csrf']) ?>">
            <input type="hidden" name="site" value="<?= e($site_atual) ?>">
            <input type="hidden" name="slug" value="<?= e($p['post_name']) ?>">
            <button type="submit">excluir</button>
          </form>
        </div>
      </div>
    <?php endforeach; ?>
  </div>
  <?php endif; ?>
<?php endif; ?>
</div>
</body>
</html>
