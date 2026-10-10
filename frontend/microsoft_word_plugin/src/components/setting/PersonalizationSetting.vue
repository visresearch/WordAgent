<template>
  <div class="personalization-container">
    <!-- 自定义指令 -->
    <section>
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
            {{ $t('personalization.instructions') }}
          </h2>
          <p class="section-subtitle">
            {{ $t('personalization.instructionsDesc') }}
          </p>
        </div>
      </div>

      <div class="setting-item">
        <label class="setting-label">
          {{ $t('personalization.globalPrompt') }}
          <span class="label-hint">{{ $t('personalization.promptHint') }}</span>
        </label>
        <textarea
          v-model="localSettings.customPrompt"
          class="custom-prompt-input"
          :placeholder="$t('personalization.promptPlaceholder')"
          rows="6"
          @input="onSettingChange"
        ></textarea>
        <div class="input-footer">
          <span class="char-count">{{ $t('personalization.chars', { count: localSettings.customPrompt.length }) }}</span>
          <button v-if="localSettings.customPrompt.length > 0" class="btn-clear" @click="clearCustomPrompt">
            <svg
              width="14"
              height="14"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z" />
            </svg>
            {{ $t('common.clear') }}
          </button>
        </div>
      </div>

      <!-- 预设模板 -->
      <div class="setting-item">
        <label class="setting-label">{{ $t('personalization.quickTemplates') }}</label>
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
    </section>

    <div class="section-divider"></div>

  </div>
</template>

<script>
import { computed, ref, watch } from 'vue';
import { t } from '../../i18n/index.js';

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
    const localSettings = ref({
      customPrompt: props.settings.customPrompt ?? ''
    });

    watch(() => props.settings, (newVal) => {
      localSettings.value.customPrompt = newVal.customPrompt ?? '';
    }, { deep: true });

    const promptTemplates = computed(() => [
      {
        id: 'academic',
        name: t('personalization.templates.academicName'),
        description: t('personalization.templates.academicDesc'),
        icon: 'M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z',
        prompt: t('personalization.templates.academicPrompt')
      },
      {
        id: 'creative',
        name: t('personalization.templates.creativeName'),
        description: t('personalization.templates.creativeDesc'),
        icon: 'M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z',
        prompt: t('personalization.templates.creativePrompt')
      },
      {
        id: 'business',
        name: t('personalization.templates.businessName'),
        description: t('personalization.templates.businessDesc'),
        icon: 'M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z',
        prompt: t('personalization.templates.businessPrompt')
      },
      {
        id: 'casual',
        name: t('personalization.templates.casualName'),
        description: t('personalization.templates.casualDesc'),
        icon: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
        prompt: t('personalization.templates.casualPrompt')
      }
    ]);

    const emitChange = () => {
      emit('update:settings', {
        customPrompt: localSettings.value.customPrompt
      });
    };

    const onSettingChange = () => {
      emitChange();
    };

    const clearCustomPrompt = () => {
      localSettings.value.customPrompt = '';
      emitChange();
    };

    const applyTemplate = (template) => {
      localSettings.value.customPrompt = template.prompt;
      emitChange();
    };

    return {
      localSettings,
      promptTemplates,
      onSettingChange,
      clearCustomPrompt,
      applyTemplate
    };
  }
};
</script>

<style scoped src="./setting.css"></style>

<style scoped>
.personalization-container {
  padding: 0;
}

.setting-item {
  margin-bottom: 24px;
}

.setting-item:last-child {
  margin-bottom: 0;
}

.setting-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333333;
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
  border: 1px solid #dddddd;
  border-radius: 6px;
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
  grid-template-columns: repeat(auto-fill, minmax(min(200px, 100%), 1fr));
  gap: 12px;
  margin-top: 8px;
}

.template-card {
  padding: 16px;
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.template-card:hover {
  background: #f8faff;
  border-color: #667eea;
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

</style>
