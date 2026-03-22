# 文策AI 官网

基于 [VitePress](https://vitepress.dev/) 构建的文策AI项目官网。

## 本地开发

```bash
cd web
pnpm install
pnpm docs:dev
```

## 构建

```bash
pnpm docs:build
```

构建产物在 `docs/.vitepress/dist` 目录下。

## 部署到 GitHub Pages

本项目已配置 GitHub Actions 自动部署。将代码推送到 `master` 分支后，会自动构建并部署到 GitHub Pages。

官网访问地址：https://visresearch.github.io/WordAgent/

