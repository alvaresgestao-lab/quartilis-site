<?php
// Endpoint de publicação para as ROTINAS automáticas (Claude na nuvem).
// A rotina faz POST aqui com uma chave secreta; o commit no GitHub é feito
// server-side (o token nunca sai deste servidor). Responde JSON.
header('Content-Type: application/json; charset=utf-8');
$CFG = @include __DIR__ . '/config.php';
if (!$CFG) { http_response_code(500); die(json_encode(['erro' => 'config ausente'])); }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  http_response_code(405); die(json_encode(['erro' => 'use POST']));
}

// autenticação por chave secreta (constante de tempo)
$chave = $_POST['chave'] ?? '';
if (empty($CFG['publish_key']) || !hash_equals($CFG['publish_key'], $chave)) {
  http_response_code(401); die(json_encode(['erro' => 'chave invalida']));
}

$SITES = [
  'blog'     => ['pasta' => 'content/posts-blog',     'url' => 'https://blog.quartilis.com.br',     'permalink' => 'data'],
  'serenata' => ['pasta' => 'content/posts-serenata', 'url' => 'https://serenata.quartilis.com.br', 'permalink' => 'simples'],
];
$site = $_POST['site'] ?? '';
if (!isset($SITES[$site])) { http_response_code(400); die(json_encode(['erro' => 'site invalido (use blog ou serenata)'])); }

$titulo = trim($_POST['titulo'] ?? '');
$texto  = trim($_POST['texto'] ?? '');
$data   = $_POST['data'] ?? date('Y-m-d');
if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $data)) $data = date('Y-m-d');
if ($titulo === '' || $texto === '') { http_response_code(400); die(json_encode(['erro' => 'titulo e texto sao obrigatorios'])); }

function slugify($t) {
  $t = mb_strtolower(trim($t));
  $t = strtr($t, ['á'=>'a','à'=>'a','ã'=>'a','â'=>'a','é'=>'e','ê'=>'e','í'=>'i','ó'=>'o','ô'=>'o','õ'=>'o','ú'=>'u','ü'=>'u','ç'=>'c','ñ'=>'n']);
  $t = preg_replace('/[^a-z0-9]+/', '-', $t);
  return trim(preg_replace('/-+/', '-', $t), '-');
}
function gh($method, $path, $body, $CFG) {
  $ch = curl_init("https://api.github.com/repos/{$CFG['repo']}/$path");
  $hdr = ['User-Agent: PainelQuartilis', 'Accept: application/vnd.github+json',
          'Authorization: Bearer ' . $CFG['github_token']];
  if ($body !== null) $hdr[] = 'Content-Type: application/json';
  curl_setopt_array($ch, [CURLOPT_CUSTOMREQUEST => $method, CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => $hdr, CURLOPT_TIMEOUT => 60]);
  if ($body !== null) curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body));
  $res = curl_exec($ch);
  $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
  curl_close($ch);
  return [$code, json_decode($res, true)];
}

$slug = slugify($titulo);
$arquivo = "{$SITES[$site]['pasta']}/{$data}-{$slug}.md";

// idempotência: se já existe um arquivo deste slug nesta data, não republica
list($code_get, ) = gh('GET', "contents/$arquivo?ref=main", null, $CFG);
if ($code_get === 200) {
  echo json_encode(['ok' => false, 'ja_existe' => true, 'arquivo' => $arquivo,
                    'mensagem' => 'Ja existe um artigo com este titulo nesta data. Nada publicado.']);
  exit;
}

$conteudo = "titulo: {$titulo}\ndata: {$data}\n---\n{$texto}\n";
list($code, $r) = gh('PUT', "contents/$arquivo", [
  'message' => "rotina: artigo '{$titulo}' ({$site})",
  'content' => base64_encode($conteudo), 'branch' => 'main',
], $CFG);

if ($code === 200 || $code === 201) {
  if ($SITES[$site]['permalink'] === 'data') {
    $url = $SITES[$site]['url'] . '/' . str_replace('-', '/', $data) . "/$slug/";
  } else {
    $url = $SITES[$site]['url'] . "/$slug/";
  }
  echo json_encode(['ok' => true, 'arquivo' => $arquivo, 'url' => $url,
                    'mensagem' => 'Artigo enviado. Entra no ar em ate 10 minutos.']);
} else {
  http_response_code(502);
  echo json_encode(['erro' => 'falha ao publicar no repositorio', 'github_status' => $code]);
}
