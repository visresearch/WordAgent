# wence_word_plugin

文策AI word 前端插件

## 构建项目

```bash
wpsjs create wence_word_plugin
```

```bash
pnpm add -D eslint-plugin-vue prettier
```

格式化检查代码

```bash
pnpm lint
```

## 运行项目

```bash
wpsjs debug
```

如果发现wps加载项不对劲，比如是旧代码，空页面，错图标等，要清除 WPS JS 加载项的 CEF 浏览器缓存。先关闭WPS和wpsjs debug，再运行：

```bash
# 关闭 WPS 后执行
rm -rf ~/.local/share/Kingsoft/wps/addons/data/linux-x64/cef/1.25/jsapi/cache
rm -rf ~/.local/share/Kingsoft/wps/addons/data/linux-x64/cef/cache/wpsoffice
rm -rf ~/.local/share/Kingsoft/wps/addons/data/linux-x64/cef/globalcache
```

## 开发文档

- [WPS 开放平台](https://open.wps.cn/)
- [WPSJS API 文档](https://qn.cache.wpscdn.cn/encs/doc/office_v19/index.htm)
- [WPSJS API 文档(新)](https://open.wps.cn/previous/docs/client/wpsLoad)