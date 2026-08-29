#!/usr/bin/env python3
"""Gera os sites estáticos dos subdomínios serenata e blog a partir do conteúdo
recuperado dos bancos WordPress. Uso: python3 build_sub.py
"""
import json, re, os, urllib.parse, html, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
WHATS = '5541991271129'
WHATS_FMT = '(41) 99127-1129'
MESES = ['', 'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
         'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

def data_pt(iso):
    a, m, d = iso[:10].split('-')
    return f'{int(d)} de {MESES[int(m)]} de {a}'

def localname(u):
    base = urllib.parse.unquote(u.split('?')[0].rsplit('/', 1)[-1])
    return re.sub(r'-\d+x\d+(?=\.\w+$)', '', base)

YT = re.compile(r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,})[^\s<]*')

def render_conteudo(raw, updir, updisk):
    s = raw.replace('\r\n', '\n')
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)                      # comentários (Gutenberg)
    s = re.sub(r'\[/?[a-z_]+[^\]]*\]', '', s)                          # shortcodes
    # imagens: aponta pro uploads local; remove se o arquivo não foi recuperado
    def img(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag)
        if not src: return ''
        name = localname(src.group(1))
        if not os.path.exists(os.path.join(updisk, name)): return ''
        alt = re.search(r'alt="([^"]*)"', tag)
        return f'<img src="{updir}uploads/{html.escape(name)}" alt="{html.escape(alt.group(1) if alt else "")}" loading="lazy">'
    s = re.sub(r'<img[^>]*>', img, s)
    s = re.sub(r'</?a[^>]*wp-content[^>]*>', '', s)                    # links pra anexos mortos
    # parágrafos (wpautop simplificado) + URLs soltas de YouTube viram player
    blocos = re.split(r'\n{2,}', s)
    out = []
    for b in blocos:
        b = b.strip()
        if not b: continue
        solo = YT.fullmatch(b.strip())
        if solo:
            vid = solo.group(1)
            out.append(f'<div class="video-frame"><iframe src="https://www.youtube.com/embed/{vid}" title="Vídeo" loading="lazy" allowfullscreen></iframe></div>')
            continue
        b = re.sub(r'(?<!["\'=])\bhttps?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,})[^\s<"]*',
                   lambda m: f'<a href="https://www.youtube.com/watch?v={m.group(1)}" target="_blank" rel="noopener">assista no YouTube</a>', b)
        if re.match(r'<(h\d|ul|ol|blockquote|figure|div|img|iframe|p)', b):
            out.append(b)
        else:
            out.append('<p>' + b.replace('\n', '<br>') + '</p>')
    return '\n'.join(out)


def slugify_py(t):
    import unicodedata
    t = unicodedata.normalize('NFD', t.lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = re.sub(r'[^a-z0-9]+', '-', t)
    return t.strip('-')

def posts_md(site):
    """Lê artigos em content/posts-<site>/*.md (formato: linhas 'titulo:' e 'data:', depois '---', depois o corpo)."""
    pasta = os.path.join(ROOT, 'content', f'posts-{site}')
    extras = []
    if not os.path.isdir(pasta): return extras
    for fn in sorted(os.listdir(pasta)):
        if not fn.endswith('.md') or fn.startswith('_'): continue
        raw = open(os.path.join(pasta, fn), encoding='utf-8').read()
        partes = raw.split('---', 1)
        cab, corpo = (partes[0], partes[1]) if len(partes) == 2 else ('', raw)
        titulo, data = '', ''
        for ln in cab.splitlines():
            if ln.lower().startswith('titulo:'): titulo = ln.split(':', 1)[1].strip()
            if ln.lower().startswith('data:'): data = ln.split(':', 1)[1].strip()
        if not titulo: continue
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', data): data = '2026-01-01'
        extras.append({'post_name': slugify_py(titulo), 'post_date': f'{data} 09:00:00',
                       'post_title': titulo, 'post_content': corpo.strip(),
                       'post_type': 'post', 'post_status': 'publish'})
    return extras

def pagina(cfg, prefix, titulo, desc, corpo, ativo=''):
    itens = ''
    for href, label in cfg['nav']:
        url = href if href.startswith('http') else prefix + href
        cls = ' class="ativo"' if label == ativo else ''
        itens += f'<li><a href="{url or prefix or "./"}"{cls}>{label}</a></li>'
    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<meta name="description" content="{html.escape(desc)[:158]}">
<link rel="canonical" href="__CANONICAL__">
<link rel="icon" type="image/png" href="{prefix}assets/favicon.png?v=1">
<link rel="apple-touch-icon" href="{prefix}assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Jost:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{prefix}assets/site.css?v=3">
<style>
.artigo{{max-width:760px;margin:0 auto;padding:40px 20px 70px}}
.artigo h1{{margin-bottom:6px}}
.artigo .data{{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--sage-escuro);margin-bottom:26px}}
.artigo p{{margin-bottom:16px}}
.artigo img{{margin:22px auto}}
.artigo h2,.artigo h3{{margin:28px 0 12px}}
.lista-posts{{max-width:860px;margin:0 auto;padding:10px 20px 70px}}
.post-card{{border-bottom:1px solid var(--creme);padding:26px 0}}
.post-card h2{{font-size:26px;margin-bottom:4px}}
.post-card a{{text-decoration:none}}
.post-card .data{{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--sage-escuro)}}
.post-card p{{color:var(--ink-suave);margin-top:8px}}
</style>
</head>
<body>
<header class="topo">
  <div class="topo-inner">
    <a class="marca" href="{prefix or './'}"><img class="marca-logo" src="{prefix}assets/logo-quartilis.png?v=1" alt=""><span class="marca-textos">{cfg['marca']}<span>{cfg['tagline']}</span></span></a>
    <input type="checkbox" id="menu-chk" aria-label="Abrir menu">
    <label for="menu-chk" class="menu-btn"><span></span><span></span><span></span></label>
    <nav><ul>{itens}</ul></nav>
  </div>
</header>
{corpo}
<footer class="rodape">
  <div class="rodape-inner">
    <div>
      <p class="marca-rodape">QUARTILIS</p>
      <p>{cfg['rodape']}</p>
    </div>
    <div>
      <p><a href="https://wa.me/{WHATS}" target="_blank" rel="noopener">WhatsApp {WHATS_FMT}</a></p>
      <p><a href="mailto:contato@quartilis.com.br">contato@quartilis.com.br</a></p>
      <p><a href="https://quartilis.com.br">Site principal: quartilis.com.br</a></p>
    </div>
  </div>
  <p class="assinatura">© Quartilis · música para eventos · Site por <a href="https://pedroalvares.com/" target="_blank" rel="noopener">Pedro Álvares</a></p>
</footer>
<div class="whats-widget" id="wwidget">
  <div class="whats-painel" id="wpainel">
    <h3>Fale com o Quartilis</h3>
    <p>Conte pra gente o motivo do contato e continue a conversa no WhatsApp.</p>
    <label for="wnome">Seu nome</label>
    <input id="wnome" type="text" placeholder="Como podemos te chamar?">
    <label for="wmotivo">Motivo do contato</label>
    <select id="wmotivo">
      <option>Casamento</option>
      <option>Serenata ou homenagem</option>
      <option>Aniversário ou data especial</option>
      <option>Evento corporativo</option>
      <option>Missa ou celebração religiosa</option>
      <option>Outro assunto</option>
    </select>
    <button class="whats-enviar" onclick="wEnviar()">Iniciar conversa</button>
  </div>
  <button class="whats-btn" onclick="wAbrir()" aria-label="Falar no WhatsApp">
  <svg viewBox="0 0 32 32" fill="currentColor"><path d="M16 3C9 3 3.3 8.7 3.3 15.7c0 2.4.7 4.7 1.9 6.7L3 29l6.8-2.1c1.9 1 4 1.6 6.2 1.6 7 0 12.7-5.7 12.7-12.7S23 3 16 3zm0 23.1c-2 0-3.9-.6-5.6-1.6l-.4-.2-4 1.2 1.2-3.9-.3-.4a10.2 10.2 0 0 1-1.6-5.5C5.3 10.1 10.1 5.3 16 5.3s10.7 4.8 10.7 10.4S21.9 26.1 16 26.1zm5.9-7.7c-.3-.2-1.9-1-2.2-1.1-.3-.1-.5-.2-.7.2-.2.3-.8 1.1-1 1.3-.2.2-.4.2-.7.1-.3-.2-1.4-.5-2.6-1.6-1-.9-1.6-1.9-1.8-2.2-.2-.3 0-.5.1-.7l.5-.6c.2-.2.2-.3.3-.6.1-.2 0-.4 0-.6l-1-2.4c-.3-.6-.5-.5-.7-.5h-.6c-.2 0-.6.1-.9.4-.3.3-1.1 1.1-1.1 2.7s1.2 3.1 1.3 3.4c.2.2 2.3 3.5 5.5 4.9.8.3 1.4.5 1.8.7.8.2 1.5.2 2 .1.6-.1 1.9-.8 2.1-1.5.3-.7.3-1.4.2-1.5l-.5-.3z"/></svg></button>
</div>
<script>
function wAbrir(){{document.getElementById('wpainel').classList.toggle('aberto')}}
function wEnviar(){{var n=document.getElementById('wnome').value.trim();var m=document.getElementById('wmotivo').value;var t='Olá! '+(n?('Meu nome é '+n+', vim'):'Vim')+' através do {cfg['origem']} e gostaria de falar sobre: '+m+'.';window.open('https://wa.me/5541991271129?text='+encodeURIComponent(t),'_blank')}}
document.addEventListener('click',function(e){{var a=e.target.closest('a[href^="https://wa.me"]');if(!a)return;e.preventDefault();document.getElementById('wpainel').classList.add('aberto');var c=document.getElementById('wnome');if(c)c.focus()}});
</script>
</body>
</html>'''

def resumo(conteudo, n=180):
    t = re.sub(r'<[^>]+>', ' ', conteudo)
    t = html.unescape(re.sub(r'\s+', ' ', t)).strip()
    return (t[:n] + '…') if len(t) > n else t

def gerar(site, cfg):
    base = os.path.join(ROOT, f'{site}.quartilis.com.br')
    updisk = os.path.join(base, 'uploads')
    os.makedirs(os.path.join(base, 'assets'), exist_ok=True)
    shutil.copy(os.path.join(ROOT, 'assets', 'site.css'), os.path.join(base, 'assets', 'site.css'))
    posts = json.load(open(os.path.join(ROOT, 'content', f'{site}-conteudo.json')))
    pages = {p['post_name']: p for p in posts if p['post_type'] == 'page'}
    extras = posts_md(site)
    slugs_md = {p['post_name'] for p in extras}
    excl = set(cfg.get('excluir_posts', []))
    arts = [p for p in posts if p['post_type'] == 'post' and p['post_name'] not in slugs_md and p['post_name'] not in excl] + extras
    arts = sorted(arts, key=lambda x: x['post_date'], reverse=True)

    def caminho_post(p):
        if cfg['permalink'] == 'data':
            a, m, d = p['post_date'][:10].split('-')
            return f'{a}/{m}/{d}/{p["post_name"]}/'
        return f'{p["post_name"]}/'

    def escrever(rel, conteudo_html):
        full = os.path.join(base, rel, 'index.html') if rel else os.path.join(base, 'index.html')
        os.makedirs(os.path.dirname(full), exist_ok=True)
        canonical = f'https://{site}.quartilis.com.br/' + rel
        conteudo_html = conteudo_html.replace('__CANONICAL__', canonical)
        open(full, 'w', encoding='utf-8').write(conteudo_html)

    # páginas estáticas
    for slug, dest, no_nav in cfg['paginas']:
        p = pages.get(slug)
        if not p: continue
        prefix = '../' * dest.count('/') if dest else ''
        corpo_html = render_conteudo(p['post_content'], prefix, updisk)
        corpo = f'<section class="secao secao-titulo"><div class="secao-inner"><h1>{html.escape(p["post_title"])}</h1></div></section><article class="artigo">{corpo_html}</article>'
        escrever(dest, pagina(cfg, prefix, f'{p["post_title"]} | {cfg["titulo"]}', resumo(corpo_html), corpo, ativo=no_nav))

    # listagem do blog
    dest = cfg['blog_dest']
    prefix = '../' * dest.count('/') if dest else ''
    cards = ''
    for p in arts:
        cam = caminho_post(p)
        corpo_render = render_conteudo(p['post_content'], '', updisk)
        cards += f'''<div class="post-card"><a href="{prefix}{cam}"><h2>{html.escape(p["post_title"])}</h2></a>
<p class="data">{data_pt(p["post_date"])}</p><p>{html.escape(resumo(corpo_render))}</p></div>'''
    corpo = f'<section class="secao secao-titulo"><div class="secao-inner"><h1>{cfg["blog_titulo"]}</h1><p class="sub">{cfg["blog_sub"]}</p></div></section><div class="lista-posts">{cards}</div>'
    escrever(dest, pagina(cfg, prefix, cfg['titulo'] if cfg['blog_titulo'] == cfg['titulo'] else f'{cfg["blog_titulo"]} | {cfg["titulo"]}', cfg['blog_sub'], corpo, ativo='Blog'))

    # posts
    for p in arts:
        cam = caminho_post(p)
        prefix = '../' * cam.count('/')
        corpo_html = render_conteudo(p['post_content'], prefix, updisk)
        corpo = f'''<article class="artigo"><h1>{html.escape(p["post_title"])}</h1>
<p class="data">{data_pt(p["post_date"])}</p>
{corpo_html}
<p style="margin-top:34px"><a class="btn" href="https://wa.me/{WHATS}?text=Olá!%20Vi%20o%20site%20e%20gostaria%20de%20um%20orçamento." target="_blank" rel="noopener">{cfg['cta']}</a></p>
<p style="margin-top:18px"><a class="link-seta" href="{prefix}{cfg['blog_dest']}">Voltar ao blog</a></p></article>'''
        escrever(cam, pagina(cfg, prefix, f'{p["post_title"]} | {cfg["titulo"]}', resumo(corpo_html), corpo))

    # .htaccess: categorias/feeds antigos -> blog
    open(os.path.join(base, '.htaccess'), 'w').write(cfg['htaccess'])
    n = sum(len(files) for _, _, files in os.walk(base))
    print(f'  {site}: {len(pages)} páginas + {len(arts)} posts gerados ({n} arquivos)')

SERENATA = {
    'titulo': 'Serenata Quartilis', 'marca': 'SERENATA', 'tagline': 'quartilis · um presente inesquecível',
    'rodape': 'Serenatas em Curitiba e região: homenagens musicais ao vivo, desde 2002.',
    'nav': [('', 'Início'), ('sugestoes-de-musicas/', 'Sugestões de Músicas'),
            ('blog/', 'Blog'), ('https://quartilis.com.br', 'Site Quartilis')],
    'paginas': [('serenata-ao-vivo', 'serenata-ao-vivo/', ''),
                ('sugestoes-de-musicas', 'sugestoes-de-musicas/', 'Sugestões de Músicas'), ('videos', 'videos/', '')],
    'excluir_posts': ['serenata-virtual', 'serenata-por-video-violino', 'serenata-com-seguranca', 'presentes-musicais-serenata'],
    'blog_dest': 'blog/', 'blog_titulo': 'Blog', 'blog_sub': 'Histórias de serenatas, homenagens e datas especiais em Curitiba.',
    'cta': 'Quero uma serenata', 'permalink': 'simples', 'origem': 'site de Serenatas do Quartilis',
    'htaccess': 'RewriteEngine On\nRewriteCond %{HTTPS} off\nRewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]\nRedirectMatch 301 ^/category/.*$ /blog/\nRedirectMatch 301 ^/(feed|comments/feed)/?$ /blog/\nRedirectMatch 301 ^/serenata-um-presente-inesquecivel/?$ /\nRedirectMatch 301 ^/serenata-por-video/?$ /\nRedirectMatch 301 ^/(serenata-virtual|serenata-por-video-violino|serenata-com-seguranca|presentes-musicais-serenata)/?$ /\nRedirectMatch 301 ^/serenata-em-curitiba/?$ /blog/serenata-em-curitiba/\n',
}
# nota: serenata posts moram na raiz (/slug/), não sob /blog/ — ajustar htaccess acima se necessário
SERENATA['htaccess'] = SERENATA['htaccess'].replace('/blog/serenata-em-curitiba/', '/serenata-em-curitiba/')

BLOG = {
    'titulo': 'Blog Quartilis', 'marca': 'BLOG', 'tagline': 'quartilis · música para eventos',
    'rodape': 'Dicas de música para casamentos e histórias de eventos reais com o Quartilis, em Curitiba.',
    'nav': [('', 'Blog'), ('https://quartilis.com.br', 'Site principal'), ('https://serenata.quartilis.com.br', 'Serenatas')],
    'paginas': [], 'blog_dest': '', 'blog_titulo': 'Blog Quartilis',
    'blog_sub': 'Dicas para a escolha da música do casamento e histórias reais de cerimônias com o Quartilis.',
    'cta': 'Pedir um orçamento', 'permalink': 'data', 'origem': 'blog do Quartilis',
    'htaccess': 'RewriteEngine On\nRewriteCond %{HTTPS} off\nRewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]\nRedirectMatch 301 ^/(inspiracoes|dicas|pagina-inicial|blog)/?$ /\nRedirectMatch 301 ^/category/.*$ /\nRedirectMatch 301 ^/(feed|comments/feed)/?$ /\n',
}

def serenata_landing():
    W = '5541991271129'
    videos = [
        ('rg6zy4aXTdE', 'Dia das Mães, serenatas com violino'),
        ('b4dl-m-UW3o', 'Violino solo'),
        ('wrZFVf03NLA', 'Violino e viola erudita'),
        ('liYQHvYVudo', 'Violino e violoncelo'),
        ('cBK1F6TSHSM', 'Voz, violão e violino'),
        ('x9wl-PqJCBU', 'Voz, violão, violino e violoncelo'),
        ('jJi-AHQrmAk', 'Voz, violão e acordeon'),
        ('bXfHG328v0A', 'Serenata de aniversário'),
        ('O98rNXGrbPA', 'Serenata ao vivo'),
        ('aHfUJnCj8Wk', 'Serenata ao vivo'),
    ]
    vids = ''
    for vid, tit in videos:
        vids += (f'<a class="card-video" href="https://www.youtube.com/watch?v={vid}" target="_blank" rel="noopener">'
                 f'<span class="thumb"><img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="{tit}" loading="lazy">'
                 f'<span class="play-mini"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></span></span>'
                 f'<span class="titulo-video">{tit}</span></a>')
    cta = f'https://wa.me/{W}?text=Ol%C3%A1!%20Gostaria%20de%20pedir%20uma%20serenata%20em%20Curitiba.'
    corpo = f'''
<section class="hero-nova">
  <div class="fundo-f" aria-hidden="true"><span>&fnof;</span><span class="espelhado">&fnof;</span></div>
  <div class="hero-grade">
    <div class="hero-esq">
      <p class="kicker">Homenagens musicais ao vivo &middot; Curitiba e regi&atilde;o</p>
      <h1>Serenata em Curitiba</h1>
      <p class="hero-sub">Um presente que emociona e marca a vida de quem voc&ecirc; ama. Do violino solo &agrave; voz e viol&atilde;o, a Quartilis leva m&uacute;sica ao vivo at&eacute; o seu momento especial, desde 2002.</p>
      <div class="hero-botoes">
        <a class="btn" href="{cta}" target="_blank" rel="noopener">Pedir uma serenata</a>
        <a class="btn btn-borda" href="#videos">Ver serenatas</a>
      </div>
    </div>
    <figure class="hero-dir foto-chanfro"><img src="assets/fotos/duo-violino-violoncelo-recepcao-casamento-curitiba.jpg" alt="Serenata com violino e violoncelo em Curitiba" fetchpriority="high"></figure>
  </div>
</section>

<section class="secao">
  <div class="secao-inner" style="max-width:800px;margin:0 auto;text-align:center">
    <h2>Um Presente Inesquec&iacute;vel</h2>
    <p class="sub" style="margin:0 auto">A serenata &eacute; uma homenagem musical ao vivo que emociona em pedidos de casamento, anivers&aacute;rios, bodas e datas especiais. Em Curitiba e regi&atilde;o, levamos m&uacute;sica de qualidade at&eacute; o momento certo, com o instrumento e o repert&oacute;rio escolhidos junto com voc&ecirc;.</p>
  </div>
</section>

<section class="secao secao-creme" id="como-funciona">
  <div class="secao-inner">
    <div class="cards-servicos">
      <div class="card-servico grande" id="ao-vivo">
        <h2>Como Funciona</h2>
        <p class="tag">Simples e pessoal</p>
        <p>Voc&ecirc; escolhe o instrumento e as m&uacute;sicas com a nossa consultoria, e n&oacute;s levamos a serenata at&eacute; o local, em Curitiba e regi&atilde;o. Recomendamos de 5 a 6 m&uacute;sicas, cerca de 15 a 20 minutos, o tempo ideal para uma homenagem inesquec&iacute;vel.</p>
      </div>
      <div class="card-servico grande" id="formacoes">
        <h2>As Forma&ccedil;&otilde;es</h2>
        <p class="tag">De 1 a 4 m&uacute;sicos</p>
        <p>Do violino solo &agrave; voz e viol&atilde;o, com saxofone ou cordas (violino, violoncelo, trio e quarteto), voc&ecirc; escolhe pela emo&ccedil;&atilde;o do momento. Para uma homenagem ainda maior, existe o concerto de presente, com um programa mais longo de m&uacute;sicas.</p>
      </div>
    </div>
    <p class="centro"><a class="btn" href="{cta}" target="_blank" rel="noopener">Falar sobre uma serenata</a></p>
  </div>
</section>

<section class="secao" id="videos">
  <div class="secao-inner">
    <h2>Veja Algumas Serenatas</h2>
    <p class="sub">Momentos reais de serenatas do Quartilis em Curitiba e regi&atilde;o.</p>
    <div class="grade-videos">{vids}</div>
  </div>
</section>

<section class="secao secao-creme">
  <div class="secao-inner duas-colunas">
    <div>
      <h2>Sugest&otilde;es de M&uacute;sicas</h2>
      <p>N&atilde;o sabe qual m&uacute;sica escolher? Reunimos sugest&otilde;es que combinam com cada tipo de homenagem para te inspirar.</p>
      <a class="link-seta" href="sugestoes-de-musicas/">Ver sugest&otilde;es de m&uacute;sicas</a>
    </div>
    <div>
      <h2>Blog das Serenatas</h2>
      <p>Hist&oacute;rias, ideias e datas especiais para presentear com m&uacute;sica em Curitiba e regi&atilde;o.</p>
      <a class="link-seta" href="blog/">Ler o blog</a>
    </div>
  </div>
</section>
'''
    pag = pagina(SERENATA, '', 'Serenata em Curitiba | Quartilis',
                 'Serenata em Curitiba e regiao: homenagem musical ao vivo para pedidos de casamento, aniversarios e datas especiais. Quartilis, desde 2002.',
                 corpo, ativo='Início')
    pag = pag.replace('__CANONICAL__', 'https://serenata.quartilis.com.br/')
    open(os.path.join(ROOT, 'serenata.quartilis.com.br', 'index.html'), 'w', encoding='utf-8').write(pag)
    print('  serenata landing (Início visual) gerada')

gerar('serenata', SERENATA)
serenata_landing()
gerar('blog', BLOG)
print('OK')
