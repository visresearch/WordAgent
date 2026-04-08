<template>
  <div class="personalization-container">
    <div class="settings-content">
      <!-- 自定义指令 -->
      <div class="setting-section">
        <div class="section-header">
          <svg
            class="section-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
          </svg>
          <div class="section-title-group">
            <h2 class="section-title">
              自定义指令
            </h2>
            <p class="section-subtitle">
              设置AI的全局提示词，影响所有对话
            </p>
          </div>
        </div>

        <div class="setting-item">
          <label class="setting-label">
            全局提示词
            <span class="label-hint">在每次对话中都会被应用，帮助AI更好地理解你的需求</span>
          </label>
          <textarea
            v-model="settings.customPrompt"
            class="custom-prompt-input"
            placeholder="例如：你是一位专业的写作助手，擅长学术写作和文档编辑。请用简洁、专业的语言回答问题..."
            rows="6"
            @input="onSettingChange"
          ></textarea>
          <div class="input-footer">
            <span class="char-count">{{ settings.customPrompt.length }} 字符</span>
            <button v-if="settings.customPrompt.length > 0" class="btn-clear" @click="clearCustomPrompt">
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z" />
              </svg>
              清空
            </button>
          </div>
        </div>

        <!-- 预设模板 -->
        <div class="setting-item">
          <label class="setting-label">快速模板</label>
          <div class="template-grid">
            <button
              v-for="template in promptTemplates"
              :key="template.id"
              class="template-card"
              @click="applyTemplate(template)"
            >
              <div class="template-header">
                <svg
                  class="template-icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path :d="template.icon" />
                </svg>
                <span class="template-name">{{ template.name }}</span>
              </div>
              <p class="template-desc">
                {{ template.description }}
              </p>
            </button>
          </div>
        </div>
      </div>

      <!-- LLM温度设置 -->
      <div class="setting-section">
        <div class="section-header">
          <svg
            class="section-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" />
          </svg>
          <div class="section-title-group">
            <h2 class="section-title">
              LLM温度
            </h2>
            <p class="section-subtitle">
              调整AI的创造性和随机性
            </p>
          </div>
        </div>

        <div class="setting-item">
          <div class="temperature-control">
            <div class="temperature-header">
              <label class="setting-label">Temperature</label>
              <span class="temperature-value">{{ settings.temperature.toFixed(2) }}</span>
            </div>

            <div class="slider-container">
              <input
                v-model.number="settings.temperature"
                type="range"
                min="0"
                max="2"
                step="0.01"
                class="temperature-slider"
                @input="onSettingChange"
              />
              <div class="slider-marks">
                <span class="mark">0</span>
                <span class="mark">0.5</span>
                <span class="mark">1</span>
                <span class="mark">1.5</span>
                <span class="mark">2</span>
              </div>
            </div>

            <div class="temperature-description">
              <div class="temp-zone" :class="{ active: settings.temperature < 0.5 }">
                <div class="zone-header">
                  <svg
                    class="zone-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <rect
                      x="3"
                      y="11"
                      width="18"
                      height="11"
                      rx="2"
                      ry="2"
                    />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  <span class="zone-name">精确模式 (0-0.5)</span>
                </div>
                <p class="zone-desc">
                  输出更确定、一致，适合事实性任务
                </p>
              </div>

              <div class="temp-zone" :class="{ active: settings.temperature >= 0.5 && settings.temperature < 1.5 }">
                <div class="zone-header">
                  <svg
                    class="zone-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                  <span class="zone-name">平衡模式 (0.5-1.5)</span>
                </div>
                <p class="zone-desc">
                  平衡准确性和创造性，适合大多数场景
                </p>
              </div>

              <div class="temp-zone" :class="{ active: settings.temperature >= 1.5 }">
                <div class="zone-header">
                  <svg
                    class="zone-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path d="M12 2L2 7l10 5 10-5-10-5z" />
                    <path d="M2 17l10 5 10-5" />
                    <path d="M2 12l10 5 10-5" />
                  </svg>
                  <span class="zone-name">创意模式 (1.5-2)</span>
                </div>
                <p class="zone-desc">
                  输出更随机、富有创造力，适合头脑风暴
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue';

export default {
  name: 'PersonalizationPane',
  props: {
    settings: {
      type: Object,
      required: true
    }
  },
  emits: ['update:settings'],
  setup(props, { emit }) {
    const settings = ref({
      customPrompt: props.settings.customPrompt ?? '',
      temperature: props.settings.temperature ?? 0.7
    });

    watch(() => props.settings, (newVal) => {
      settings.value.customPrompt = newVal.customPrompt ?? '';
      settings.value.temperature = newVal.temperature ?? 0.7;
    }, { deep: true });

    const promptTemplates = ref([
      {
        id: 'academic',
        name: '学术写作',
        description: '专业、严谨的学术风格',
        icon: 'M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z',
        prompt: '你是一位专业的学术写作助手，擅长撰写和编辑学术论文。请使用正式、严谨的学术语言，注重逻辑性和准确性。在回答问题时，优先考虑学术规范和专业术语的正确使用。'
      },
      {
        id: 'creative',
        name: '创意写作',
        description: '富有想象力的创作风格',
        icon: 'M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z',
        prompt: '你是一位富有创造力的写作助手，擅长创意写作和文学创作。请用生动、形象的语言表达，注重文采和艺术性。在协助写作时，鼓励创新思维和独特视角。'
      },
      {
        id: 'business',
        name: '商务文档',
        description: '简洁、专业的商务风格',
        icon: 'M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z',
        prompt: '你是一位专业的商务写作助手，擅长撰写商务文档、报告和邮件。请使用简洁、清晰的商务语言，注重效率和专业性。在协助写作时，确保内容条理清晰、重点突出。'
      },
      {
        id: 'casual',
        name: '日常交流',
        description: '轻松、友好的对话风格',
        icon: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
        prompt: '你是一位友好、平易近人的写作助手。请使用轻松、自然的语言风格，就像朋友之间的对话一样。在协助写作时，注重可读性和亲和力。'
      }
    ]);

    const emitChange = () => {
      emit('update:settings', {
        customPrompt: settings.value.customPrompt,
        temperature: settings.value.temperature
      });
    };

    const onSettingChange = () => {
      emitChange();
    };

    const clearCustomPrompt = () => {
      if (confirm('确定要清空自定义指令吗？')) {
        settings.value.customPrompt = '';
        emitChange();
      }
    };

    const applyTemplate = (template) => {
      if (settings.value.customPrompt && !confirm('应用模板将覆盖当前的自定义指令，是否继续？')) {
        return;
      }
      settings.value.customPrompt = template.prompt;
      emitChange();
    };

    return {
      settings,
      promptTemplates,
      onSettingChange,
      clearCustomPrompt,
      applyTemplate
    };
  }
};
</script>

<style scoped>
.personalization-container {
  padding: 0;
}

.settings-content {
  display: flex;
  flex-direction: column;
}

.setting-section {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f0f0f0;
}

.section-icon {
  width: 24px;
  height: 24px;
  color: #667eea;
  flex-shrink: 0;
  margin-top: 2px;
}

.section-title-group {
  flex: 1;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: #2c3e50;
}

.section-subtitle {
  font-size: 13px;
  color: #7f8c8d;
  margin: 0;
}

.setting-item {
  margin-bottom: 20px;
}

.setting-item:last-child {
  margin-bottom: 0;
}

.setting-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #34495e;
  margin-bottom: 8px;
}

.label-hint {
  display: block;
  font-size: 12px;
  font-weight: 400;
  color: #95a5a6;
  margin-top: 4px;
}

.custom-prompt-input {
  width: 100%;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  resize: vertical;
  transition: all 0.3s ease;
}

.custom-prompt-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.custom-prompt-input::placeholder {
  color: #bdc3c7;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.char-count {
  font-size: 12px;
  color: #95a5a6;
}

.btn-clear {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  background: transparent;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  color: #7f8c8d;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-clear:hover {
  background: #fee;
  border-color: #e74c3c;
  color: #e74c3c;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.template-card {
  padding: 16px;
  background: #f8f9fa;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.template-card:hover {
  background: #e3f2fd;
  border-color: #667eea;
  transform: translateY(-2px);
}

.template-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.template-icon {
  width: 18px;
  height: 18px;
  color: #667eea;
}

.template-name {
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
}

.template-desc {
  font-size: 12px;
  color: #7f8c8d;
  margin: 0;
  line-height: 1.4;
}

.temperature-control {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
}

.temperature-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.temperature-value {
  font-size: 24px;
  font-weight: 600;
  color: #667eea;
}

.slider-container {
  margin-bottom: 24px;
}

.temperature-slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(to right, #3498db, #2ecc71, #f39c12, #e74c3c);
  outline: none;
  appearance: none;
  -webkit-appearance: none;
  margin: 8px 0;
}

.temperature-slider::-webkit-slider-thumb {
  appearance: none;
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: white;
  border: 3px solid #667eea;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.temperature-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: white;
  border: 3px solid #667eea;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.slider-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
}

.mark {
  font-size: 12px;
  color: #95a5a6;
}

.temperature-description {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.temp-zone {
  padding: 12px;
  background: white;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.temp-zone.active {
  border-color: #667eea;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15);
}

.zone-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.zone-icon {
  width: 16px;
  height: 16px;
  color: #667eea;
}

.zone-name {
  font-size: 13px;
  font-weight: 600;
  color: #2c3e50;
}

.zone-desc {
  font-size: 12px;
  color: #7f8c8d;
  margin: 0;
  line-height: 1.5;
}

/* 滚动条样式 */
.settings-content::-webkit-scrollbar {
  width: 8px;
}

.settings-content::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.settings-content::-webkit-scrollbar-thumb {
  background: #bdc3c7;
  border-radius: 4px;
}

.settings-content::-webkit-scrollbar-thumb:hover {
  background: #95a5a6;
}
</style>
