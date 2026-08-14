# Quartilis — Site estático

Site da Quartilis (música para eventos e casamentos, Curitiba) reconstruído como site estático, substituindo o Drupal 7.

- **Produção:** quartilis.com.br (hospedagem cPanel/LiteSpeed da Ana)
- **Deploy:** GitHub Actions → FTP (a cada push na `main`), workflow em `.github/workflows/deploy.yml`
- **Repertório:** `repertorio/` — 650 músicas com 796 vídeos, dados em `clients/quartilis/prototipo-repertorio/dados-musicas.json` no Brain
- **Subdomínios a recuperar:** serenata.quartilis.com.br e blog.quartilis.com.br (conteúdo resgatado do Wayback Machine)

## Estrutura planejada

```
/                → Home
/musicos/        → Músicos
/servicos/       → Serviços
/fotos-e-videos/ → Fotos e Vídeos
/repertorio/     → Repertório (pronto)
/contato/        → Contato
```

URLs antigas do Drupal (`/quartilis/...`) recebem 301 via `.htaccess`.
