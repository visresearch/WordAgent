# wps_word_plugin

文策AI WPS word 前端加载项

## 构建项目

```bash
pnpm install
```

```bash
pnpm add -D eslint-plugin-vue prettier
```

格式化规范代码

```bash
pnpm lint
```

## 运行项目

```bash
npm install -g wpsjs
wpsjs debug
```

## 项目发布

```bash
wpsjs publish
```

生成一个html文件后，上传到fastapi后端上，让后端QT界面加载这个html安装页面

## 注意事项

- 如果发现wps加载项不对劲，比如是旧代码，空页面，错图标等，要清除 WPS JS 加载项的 CEF 浏览器缓存。先关闭WPS和wpsjs debug，再运行：

```bash
# 关闭 WPS 后执行
rm -rf ~/.local/share/Kingsoft/wps/addons/data/linux-x64/cef/1.25/jsapi/cache
rm -rf ~/.local/share/Kingsoft/wps/addons/data/linux-x64/cef/cache/wpsoffice
rm -rf ~/.local/share/Kingsoft/wps/addons/data/linux-x64/cef/globalcache
```

- 如果发现WPS加载项没显示出来，在WPS中点击工具->加载项，找到相对应链接加载项，点击启用，重启WPS即可看到加载项。

## 开发文档

- [WPS 开放平台](https://open.wps.cn/)
- [WPSJS API 文档](https://qn.cache.wpscdn.cn/encs/doc/office_v19/index.htm)
- [WPSJS API 文档(新)](https://open.wps.cn/previous/docs/client/wpsLoad)