<template>
  <div class="about-container">
    <div class="about-content">
      <!-- 项目图标和名称 -->
      <div class="project-info">
        <div class="project-icon">
          <img class="icon-logo" src="/images/robot.svg" alt="WenCe AI" />
        </div>
        <h1 class="project-name">
          文策AI助手
        </h1>
        <p class="project-subtitle">
          WenCe AI Assistant
        </p>
      </div>

      <!-- 版本信息 -->
      <div class="info-section">
        <div class="info-item">
          <span class="info-label">版本号</span>
          <span class="info-value">{{ version }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">插件类型</span>
          <span class="info-value">WPS 文字加载项</span>
        </div>
        <div class="info-item">
          <span class="info-label">开发者</span>
          <span class="info-value">日月星辰</span>
        </div>
      </div>

      <!-- 项目链接 -->
      <div class="links-section">
        <h3>🔗 相关链接</h3>
        <div class="link-list">
          <a
            href="https://github.com/visresearch/WordAgent"
            target="_blank"
            rel="noopener noreferrer"
            class="link-item"
            @click.prevent="openExternalLink('https://github.com/visresearch/WordAgent')"
          >
            <img class="link-icon" :src="githubIcon" alt="GitHub" />
            <span>GitHub 仓库</span>
          </a>
          <a
            href="https://visresearch.github.io/WordAgent/"
            target="_blank"
            rel="noopener noreferrer"
            class="link-item"
            @click.prevent="openExternalLink('https://visresearch.github.io/WordAgent/')"
          >
            <img class="link-icon" :src="webIcon" alt="项目官网" />
            <span>项目官网</span>
          </a>
          <a
            href="https://visresearch.github.io/WordAgent/guide/wps-plugin.html"
            target="_blank"
            rel="noopener noreferrer"
            class="link-item"
            @click.prevent="openExternalLink('https://visresearch.github.io/WordAgent/guide/wps-plugin.html')"
          >
            <img class="link-icon" :src="helpIcon" alt="使用文档" />
            <span>使用文档</span>
          </a>
          <a
            href="https://github.com/visresearch/WordAgent/issues"
            target="_blank"
            rel="noopener noreferrer"
            class="link-item"
            @click.prevent="openExternalLink('https://github.com/visresearch/WordAgent/issues')"
          >
            <img class="link-icon" :src="issueIcon" alt="问题反馈" />
            <span>问题反馈</span>
          </a>
          <a
            href="https://visresearch.github.io/WordAgent/guide/sponsor.html"
            target="_blank"
            rel="noopener noreferrer"
            class="link-item"
            @click.prevent="openExternalLink('https://visresearch.github.io/WordAgent/guide/sponsor.html')"
          >
            <img class="link-icon" :src="sponsorIcon" alt="赞助作者" />
            <span>赞助作者</span>
          </a>
        </div>
      </div>

      <!-- 版权信息 -->
      <div class="copyright">
        <p>© 2026 WenCe Team. All rights reserved.</p>
        <p class="license">
          Licensed under MIT License
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import githubIcon from '../../assets/icons/github.svg';
import webIcon from '../../assets/icons/web.svg';
import helpIcon from '../../assets/icons/help.svg';
import issueIcon from '../../assets/icons/issue.svg';
import sponsorIcon from '../../assets/icons/sponsor.svg';
import api from '../js/api.js';

export default {
  name: 'AboutPane',
  data() {
    return {
      version: '未知版本',
      githubIcon,
      webIcon,
      helpIcon,
      issueIcon,
      sponsorIcon
    };
  },
  mounted() {
    this.loadVersion();
  },
  methods: {
    async loadVersion() {
      const result = await api.getAppVersion();
      const version = result.success ? result.data?.version : '';
      if (version) {
        this.version = version;
      }
    },
    closeDialog() {
      // 关闭 WPS 对话框
      try {
        window.close();
      } catch (e) {
        console.error('关闭对话框失败:', e);
      }
    },
    openExternalLink(url) {
      try {
        const opened = window.open(url, '_blank', 'noopener,noreferrer');
        // 某些宿主环境中 window.open 可能返回 null，兜底到当前窗口跳转
        if (!opened) {
          window.location.href = url;
        }
      } catch (e) {
        console.error('打开外部链接失败:', e);
      }
    }
  }
};
</script>

<style scoped>
.about-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100%;
  background: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
  overflow: hidden;
}

.about-content {
  flex: 1;
  overflow-y: auto;
  padding: 32px 24px;
  background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 项目信息 */
.project-info {
  text-align: center;
  margin-bottom: 32px;
}

.project-icon {
  width: 100px;
  height: 100px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.25);
}

.icon-logo {
  width: 60px;
  height: 60px;
  fill: white;
}

.project-name {
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 700;
  color: #333;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.project-subtitle {
  margin: 0;
  font-size: 14px;
  color: #888;
  font-weight: 500;
  letter-spacing: 1px;
}

/* 信息区域 */
.info-section {
  width: 100%;
  max-width: 400px;
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

/* 链接区域 */
.links-section {
  width: 100%;
  max-width: 400px;
  margin-bottom: 24px;
}

.links-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #333;
  font-weight: 600;
}

.link-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.link-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: white;
  border-radius: 10px;
  text-decoration: none;
  color: #5f69d9;
  transition: all 0.2s;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.link-item:visited {
  color: #5f69d9;
}

.link-item:hover {
  background: #f6f5ff;
  color: #6c52dd;
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.link-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  filter: brightness(0) saturate(100%) invert(45%) sepia(60%) saturate(855%) hue-rotate(214deg) brightness(95%) contrast(92%);
}

.link-item:hover .link-icon {
  filter: brightness(0) saturate(100%) invert(38%) sepia(49%) saturate(1068%) hue-rotate(228deg) brightness(99%) contrast(95%);
}

.link-item span {
  font-size: 14px;
  font-weight: 500;
}

/* 版权信息 */
.copyright {
  text-align: center;
  margin-top: auto;
  padding-top: 24px;
}

.copyright p {
  margin: 4px 0;
  font-size: 12px;
  color: #999;
}

.license {
  color: #bbb;
}
</style>
