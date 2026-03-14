<template>
  <div class="personalization-container">
    <div class="section-header">
      <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
      <div class="section-title-group">
        <h2 class="section-title">个性化定制</h2>
        <p class="section-subtitle">自定义AI助手的行为方式和响应风格</p>
      </div>
    </div>

    <!-- 全局提示词 -->
    <div class="prompt-section">
      <div class="prompt-header">
        <span class="prompt-label">全局提示词</span>
        <span class="prompt-hint">设定AI助手的角色、写作风格或特殊要求</span>
      </div>
      <textarea
        v-model="localSettings.customPrompt"
        class="prompt-textarea"
        placeholder="例如：你是一位专业的学术写作助手，擅长论文润色和格式调整..."
        rows="4"
        @input="emitChange"
      ></textarea>
      <div class="prompt-templates">
        <span class="templates-label">快速模板：</span>
        <button v-for="tpl in templates" :key="tpl.name" class="template-btn" @click="applyTemplate(tpl.content)">
          {{ tpl.name }}
        </button>
      </div>
    </div>

    <!-- Temperature 控制 -->
    <div class="temperature-section">
      <div class="temp-header">
        <span class="temp-label">LLM Temperature</span>
        <span class="temp-value">{{ localSettings.temperature.toFixed(1) }}</span>
      </div>
      <div class="temp-slider-wrapper">
        <input
          v-model.number="localSettings.temperature"
          type="range"
          class="temp-slider"
          min="0"
          max="2"
          step="0.1"
          @input="emitChange"
        />
        <div class="temp-zones">
          <span class="zone" :class="{ active: localSettings.temperature <= 0.5 }">精确模式</span>
          <span class="zone" :class="{ active: localSettings.temperature > 0.5 && localSettings.temperature <= 1.2 }">平衡模式</span>
          <span class="zone" :class="{ active: localSettings.temperature > 1.2 }">创意模式</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue';

export default {
  name: 'PersonalizationSetting',
  props: {
    settings: { type: Object, required: true }
  },
  emits: ['update:settings'],
  setup(props, { emit }) {
    const localSettings = ref({
      customPrompt: props.settings.customPrompt ?? '',
      temperature: props.settings.temperature ?? 0.7
    });

    const templates = [
      { name: '学术写作', content: '你是一位专业的学术写作助手，擅长论文润色、格式调整和学术表达优化。请使用严谨、客观的学术语言，注意引用规范和逻辑严密性。' },
      { name: '创意写作', content: '你是一位富有创意的写作伙伴，擅长生动的描述、巧妙的修辞和引人入胜的叙事。请在保持内容准确性的前提下，尽量使文字生动有趣。' },
      { name: '商务文档', content: '你是一位专业的商务文档写作助手，擅长撰写清晰、专业的商务文档，包括邮件、报告、方案等。请使用简洁明了的商务语言。' },
      { name: '日常交流', content: '你是一位友善的AI助手，用自然、亲切的语言与用户交流。回答简洁明了，必要时提供详细解释。' }
    ];

    watch(() => props.settings, (newVal) => {
      localSettings.value.customPrompt = newVal.customPrompt ?? '';
      localSettings.value.temperature = newVal.temperature ?? 0.7;
    }, { deep: true });

    const emitChange = () => {
      emit('update:settings', {
        customPrompt: localSettings.value.customPrompt,
        temperature: localSettings.value.temperature
      });
    };

    const applyTemplate = (content) => {
      localSettings.value.customPrompt = content;
      emitChange();
    };

    return { localSettings, templates, emitChange, applyTemplate };
  }
};
</script>

<style scoped>
.personalization-container { padding: 0; }

.section-header {
  display: flex; align-items: flex-start; gap: 16px;
  margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid #f0f0f0;
}
.section-icon { width: 24px; height: 24px; color: #667eea; flex-shrink: 0; margin-top: 2px; }
.section-title-group { flex: 1; }
.section-title { font-size: 18px; font-weight: 600; margin: 0 0 4px; color: #2c3e50; }
.section-subtitle { font-size: 13px; color: #7f8c8d; margin: 0; }

.prompt-section { margin-bottom: 32px; }
.prompt-header { margin-bottom: 8px; }
.prompt-label { font-size: 14px; font-weight: 500; color: #333; }
.prompt-hint { font-size: 11px; color: #999; margin-left: 8px; }
.prompt-textarea {
  width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px;
  font-size: 13px; color: #333; background: #fafafa; outline: none; resize: vertical;
  font-family: inherit; line-height: 1.5; transition: border-color 0.2s;
  box-sizing: border-box;
}
.prompt-textarea:focus { border-color: #667eea; background: white; }
.prompt-textarea::placeholder { color: #bbb; }

.prompt-templates {
  display: flex; align-items: center; gap: 8px; margin-top: 8px; flex-wrap: wrap;
}
.templates-label { font-size: 12px; color: #888; }
.template-btn {
  padding: 4px 10px; background: #f0f4ff; color: #667eea; border: 1px solid #d0d8f0;
  border-radius: 12px; font-size: 11px; cursor: pointer; transition: all 0.2s;
}
.template-btn:hover { background: #667eea; color: white; border-color: #667eea; }

.temperature-section {
  background: #f8f9fa; border-radius: 8px; padding: 16px; border: 1px solid #e8e8e8;
}
.temp-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
}
.temp-label { font-size: 14px; font-weight: 500; color: #333; }
.temp-value {
  font-size: 16px; font-weight: 600; color: #667eea;
  background: #f0f4ff; padding: 2px 10px; border-radius: 12px;
}
.temp-slider-wrapper { padding: 0 4px; }
.temp-slider {
  width: 100%; height: 6px; -webkit-appearance: none; appearance: none;
  background: linear-gradient(to right, #27ae60 0%, #f39c12 50%, #e74c3c 100%);
  border-radius: 3px; outline: none;
}
.temp-slider::-webkit-slider-thumb {
  -webkit-appearance: none; width: 18px; height: 18px; border-radius: 50%;
  background: white; border: 2px solid #667eea; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
.temp-zones {
  display: flex; justify-content: space-between; margin-top: 8px;
}
.zone {
  font-size: 11px; color: #bbb; transition: color 0.2s;
}
.zone.active { color: #667eea; font-weight: 600; }
</style>
