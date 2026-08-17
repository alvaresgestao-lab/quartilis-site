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
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect width=%22100%22 height=%22100%22 fill=%22%23dfddd0%22/><text y=%2272%22 x=%2250%22 text-anchor=%22middle%22 font-size=%2260%22>🎻</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Jost:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{prefix}assets/site.css?v=2">
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
    <a class="marca" href="{prefix or './'}">{cfg['marca']}<span>{cfg['tagline']}</span></a>
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
  <p class="assinatura">© Quartilis · música para eventos</p>
</footer>
<a class="whats-flutuante" href="https://wa.me/{WHATS}" target="_blank" rel="noopener" aria-label="WhatsApp">
<svg viewBox="0 0 32 32" fill="currentColor"><path d="M16 3C9 3 3.3 8.7 3.3 15.7c0 2.4.7 4.7 1.9 6.7L3 29l6.8-2.1c1.9 1 4 1.6 6.2 1.6 7 0 12.7-5.7 12.7-12.7S23 3 16 3zm0 23.1c-2 0-3.9-.6-5.6-1.6l-.4-.2-4 1.2 1.2-3.9-.3-.4a10.2 10.2 0 0 1-1.6-5.5C5.3 10.1 10.1 5.3 16 5.3s10.7 4.8 10.7 10.4S21.9 26.1 16 26.1zm5.9-7.7c-.3-.2-1.9-1-2.2-1.1-.3-.1-.5-.2-.7.2-.2.3-.8 1.1-1 1.3-.2.2-.4.2-.7.1-.3-.2-1.4-.5-2.6-1.6-1-.9-1.6-1.9-1.8-2.2-.2-.3 0-.5.1-.7l.5-.6c.2-.2.2-.3.3-.6.1-.2 0-.4 0-.6l-1-2.4c-.3-.6-.5-.5-.7-.5h-.6c-.2 0-.6.1-.9.4-.3.3-1.1 1.1-1.1 2.7s1.2 3.1 1.3 3.4c.2.2 2.3 3.5 5.5 4.9.8.3 1.4.5 1.8.7.8.2 1.5.2 2 .1.6-.1 1.9-.8 2.1-1.5.3-.7.3-1.4.2-1.5l-.5-.3z"/></svg></a>
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
    arts = sorted([p for p in posts if p['post_type'] == 'post'], key=lambda x: x['post_date'], reverse=True)

    def caminho_post(p):
        if cfg['permalink'] == 'data':
            a, m, d = p['post_date'][:10].split('-')
            return f'{a}/{m}/{d}/{p["post_name"]}/'
        return f'{p["post_name"]}/'

    def escrever(rel, conteudo_html):
        full = os.path.join(base, rel, 'index.html') if rel else os.path.join(base, 'index.html')
        os.makedirs(os.path.dirname(full), exist_ok=True)
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
    'rodape': 'Serenatas em Curitiba e região: homenagens musicais ao vivo ou por vídeo, desde 2002.',
    'nav': [('', 'Apresentação'), ('serenata-ao-vivo/', 'Serenata ao vivo'), ('serenata-por-video/', 'Serenata por Vídeo'),
            ('sugestoes-de-musicas/', 'Sugestões de músicas'), ('videos/', 'Vídeos'), ('blog/', 'Blog')],
    'paginas': [('pagina-inicial', '', 'Apresentação'), ('serenata-ao-vivo', 'serenata-ao-vivo/', 'Serenata ao vivo'),
                ('serenata-por-video', 'serenata-por-video/', 'Serenata por Vídeo'),
                ('sugestoes-de-musicas', 'sugestoes-de-musicas/', 'Sugestões de músicas'), ('videos', 'videos/', 'Vídeos')],
    'blog_dest': 'blog/', 'blog_titulo': 'Blog', 'blog_sub': 'Histórias de serenatas, homenagens e datas especiais em Curitiba.',
    'cta': 'Quero uma serenata', 'permalink': 'simples',
    'htaccess': 'RewriteEngine On\nRewriteCond %{HTTPS} off\nRewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]\nRedirectMatch 301 ^/category/.*$ /blog/\nRedirectMatch 301 ^/(feed|comments/feed)/?$ /blog/\nRedirectMatch 301 ^/serenata-um-presente-inesquecivel/?$ /\nRedirectMatch 301 ^/serenata-em-curitiba/?$ /blog/serenata-em-curitiba/\n',
}
# nota: serenata posts moram na raiz (/slug/), não sob /blog/ — ajustar htaccess acima se necessário
SERENATA['htaccess'] = SERENATA['htaccess'].replace('/blog/serenata-em-curitiba/', '/serenata-em-curitiba/')

BLOG = {
    'titulo': 'Blog Quartilis', 'marca': 'BLOG', 'tagline': 'quartilis · música para eventos',
    'rodape': 'Dicas de música para casamentos e histórias de eventos reais com o Quartilis, em Curitiba.',
    'nav': [('', 'Blog'), ('https://quartilis.com.br', 'Site principal'), ('https://serenata.quartilis.com.br', 'Serenatas')],
    'paginas': [], 'blog_dest': '', 'blog_titulo': 'Blog Quartilis',
    'blog_sub': 'Dicas para a escolha da música do casamento e histórias reais de cerimônias com o Quartilis.',
    'cta': 'Pedir um orçamento', 'permalink': 'data',
    'htaccess': 'RewriteEngine On\nRewriteCond %{HTTPS} off\nRewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]\nRedirectMatch 301 ^/(inspiracoes|dicas|pagina-inicial|blog)/?$ /\nRedirectMatch 301 ^/category/.*$ /\nRedirectMatch 301 ^/(feed|comments/feed)/?$ /\n',
}

gerar('serenata', SERENATA)
gerar('blog', BLOG)
print('OK')
