<template>
  <Teleport to="body">
    <div class="model-parameter-overlay" @click.self="$emit('close')">
      <form
        ref="dialog"
        class="model-parameter-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="model-parameter-title"
        @submit.prevent="confirmSettings"
        @keydown="onKeydown"
      >
        <header class="dialog-header">
          <div class="dialog-heading">
            <h3 id="model-parameter-title">
              {{ $t('model.parameters.editTitle', { name: model.name || model.id }) }}
            </h3>
            <p class="model-identity">
              <span v-if="providerName">{{ providerName }} · </span>{{ model.id }}
            </p>
          </div>
          <button
            type="button"
            class="dialog-close"
            :aria-label="$t('common.close')"
            @click="$emit('close')"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              aria-hidden="true"
            >
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </header>

        <div class="dialog-body">
          <div
            v-for="parameter in samplingParameters"
            :key="parameter.key"
            class="parameter-field sampling-field"
          >
            <div class="parameter-description">
              <label :for="`model-${parameter.key}-slider`">{{ parameter.label }}</label>
              <p :id="`model-${parameter.key}-hint`" class="field-hint">
                {{ $t(parameter.hint) }}
              </p>
            </div>
            <div class="parameter-control sampling-control">
              <div class="range-control">
                <span class="range-limit" aria-hidden="true">0</span>
                <input
                  :id="`model-${parameter.key}-slider`"
                  v-model.number="draft[parameter.key]"
                  class="parameter-range"
                  type="range"
                  min="0"
                  :max="parameter.max"
                  step="0.01"
                  :style="{ '--range-progress': `${rangeProgress(parameter)}%` }"
                  :aria-describedby="`model-${parameter.key}-hint`"
                />
                <span class="range-limit" aria-hidden="true">{{ parameter.max }}</span>
              </div>
              <input
                :id="`model-${parameter.key}-value`"
                v-model.number="draft[parameter.key]"
                class="sampling-value"
                type="number"
                min="0"
                :max="parameter.max"
                step="0.01"
                required
                :aria-label="$t('model.parameters.numericValue', { name: parameter.label })"
                :aria-describedby="`model-${parameter.key}-hint`"
              />
            </div>
          </div>

          <div class="parameter-field">
            <div class="parameter-description">
              <label for="model-max-tokens">Max Tokens</label>
              <p id="model-max-tokens-hint" class="field-hint">
                {{ $t('model.parameters.maxTokensHint') }}
              </p>
            </div>
            <div class="parameter-control token-input">
              <input
                id="model-max-tokens"
                v-model.number="draft.maxTokens"
                type="number"
                min="1"
                :max="maxSafeInteger"
                step="1"
                placeholder="8192"
                aria-describedby="model-max-tokens-hint"
              />
              <span aria-hidden="true">Tokens</span>
            </div>
          </div>

          <div class="parameter-field">
            <div class="parameter-description">
              <label id="model-reasoning-label" for="model-reasoning-effort">Reasoning Effort</label>
              <p id="model-reasoning-hint" class="field-hint">
                {{ $t('model.parameters.reasoningHint') }}
              </p>
            </div>
            <div class="parameter-control">
              <button
                id="model-reasoning-effort"
                ref="reasoningTrigger"
                type="button"
                class="reasoning-trigger"
                role="combobox"
                aria-haspopup="listbox"
                :aria-expanded="reasoningOpen"
                aria-controls="model-reasoning-options"
                :aria-activedescendant="reasoningOpen ? `model-reasoning-option-${activeReasoningIndex}` : undefined"
                aria-labelledby="model-reasoning-label"
                aria-describedby="model-reasoning-hint"
                @click="toggleReasoningMenu"
                @keydown="onReasoningKeydown"
              >
                <span>{{ draft.reasoningEffort }}</span>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.8"
                  aria-hidden="true"
                >
                  <path d="m6 9 6 6 6-6" />
                </svg>
              </button>
              <Teleport to="body">
                <div
                  v-if="reasoningOpen"
                  id="model-reasoning-options"
                  ref="reasoningMenu"
                  class="reasoning-menu"
                  role="listbox"
                  aria-labelledby="model-reasoning-label"
                  :style="reasoningMenuStyle"
                  @pointerdown.stop
                  @mousedown.stop.prevent
                  @mouseup.stop
                  @click.stop.prevent
                >
                  <div
                    v-for="(effort, index) in reasoningOptions"
                    :id="`model-reasoning-option-${index}`"
                    :key="effort"
                    class="reasoning-option"
                    :class="{ 'is-active': index === activeReasoningIndex, 'is-selected': effort === draft.reasoningEffort }"
                    role="option"
                    :aria-selected="effort === draft.reasoningEffort"
                    @mouseenter="activeReasoningIndex = index"
                    @pointerdown.stop.prevent
                    @click.stop.prevent="selectReasoning(index)"
                  >
                    {{ effort }}
                    <span v-if="effort === draft.reasoningEffort" aria-hidden="true">✓</span>
                  </div>
                </div>
              </Teleport>
            </div>
          </div>
        </div>

        <footer class="dialog-footer">
          <button type="button" class="dialog-button cancel-button" @click="$emit('close')">
            {{ $t('common.cancel') }}
          </button>
          <button type="submit" class="dialog-button confirm-button">
            {{ $t('common.confirm') }}
          </button>
        </footer>
      </form>
    </div>
  </Teleport>
</template>

<script>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue';

export default {
  name: 'ModelParameterDialog',
  props: {
    model: { type: Object, required: true },
    providerName: { type: String, default: '' }
  },
  emits: ['confirm', 'close'],
  setup(props, { emit }) {
    const dialog = ref(null);
    const reasoningTrigger = ref(null);
    const reasoningMenu = ref(null);
    const reasoningOpen = ref(false);
    const activeReasoningIndex = ref(0);
    const reasoningMenuStyle = reactive({});
    const previousFocus = document.activeElement;
    const parameters = props.model.parameters || {};
    const maxSafeInteger = Number.MAX_SAFE_INTEGER;
    const validNumber = (value, fallback, max = maxSafeInteger, integer = false, min = 0) => {
      const number = Number(value);
      return value !== null && value !== undefined && value !== ''
        && Number.isFinite(number) && number >= min && number <= max
        && (!integer || Number.isSafeInteger(number)) ? number : fallback;
    };
    // A separate draft ensures closing or cancelling never mutates the selected model.
    const reasoningOptions = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh'];
    const draft = reactive({
      temperature: validNumber(parameters.temperature, 0.5, 2),
      topP: validNumber(parameters.topP, 1, 1),
      maxTokens: validNumber(parameters.maxTokens, 8192, maxSafeInteger, true, 1),
      reasoningEffort: reasoningOptions.includes(parameters.reasoningEffort) ? parameters.reasoningEffort : 'medium'
    });
    const samplingParameters = [
      { key: 'temperature', label: 'Temperature', max: 2, hint: 'model.parameters.temperatureHint' },
      { key: 'topP', label: 'Top-p', max: 1, hint: 'model.parameters.topPHint' }
    ];
    const rangeProgress = (parameter) => {
      return Math.min(100, Math.max(0, (Number(draft[parameter.key]) || 0) / parameter.max * 100));
    };

    const closeReasoningMenu = () => {
      reasoningOpen.value = false;
    };

    const positionReasoningMenu = () => {
      if (!reasoningOpen.value || !reasoningTrigger.value) {
        return;
      }
      const anchor = reasoningTrigger.value.getBoundingClientRect();
      const body = dialog.value.querySelector('.dialog-body').getBoundingClientRect();
      if (anchor.bottom <= body.top || anchor.top >= body.bottom) {
        closeReasoningMenu();
        return;
      }
      // The teleported menu can escape the editor, but stays inside the settings viewport.
      const margin = 8;
      const gap = 4;
      const viewportWidth = document.documentElement.clientWidth;
      const viewportHeight = document.documentElement.clientHeight;
      const belowTop = Math.max(margin, anchor.bottom + gap);
      const aboveBottom = Math.min(viewportHeight - margin, anchor.top - gap);
      const below = Math.max(0, viewportHeight - margin - belowTop);
      const above = Math.max(0, aboveBottom - margin);
      const opensBelow = below >= 120 || below >= above;
      const width = Math.min(anchor.width, Math.max(0, viewportWidth - margin * 2));
      Object.assign(reasoningMenuStyle, {
        left: `${Math.max(margin, Math.min(anchor.left, viewportWidth - margin - width))}px`,
        width: `${width}px`,
        top: opensBelow ? `${belowTop}px` : undefined,
        bottom: opensBelow ? undefined : `${viewportHeight - aboveBottom}px`,
        maxHeight: `${Math.min(180, opensBelow ? below : above)}px`
      });
      nextTick(revealActiveReasoning);
    };

    const revealActiveReasoning = () => {
      const menu = reasoningMenu.value;
      const option = menu?.children[activeReasoningIndex.value];
      if (!option) {
        return;
      }
      // Scroll only the list; scrollIntoView would also move the editor/page.
      const padding = 4;
      if (option.offsetTop - padding < menu.scrollTop) {
        menu.scrollTop = option.offsetTop - padding;
      } else if (option.offsetTop + option.offsetHeight + padding > menu.scrollTop + menu.clientHeight) {
        menu.scrollTop = option.offsetTop + option.offsetHeight + padding - menu.clientHeight;
      }
    };

    const openReasoningMenu = () => {
      activeReasoningIndex.value = reasoningOptions.indexOf(draft.reasoningEffort);
      reasoningOpen.value = true;
      positionReasoningMenu();
    };

    const toggleReasoningMenu = () => {
      if (reasoningOpen.value) {
        closeReasoningMenu();
      } else {
        openReasoningMenu();
      }
    };

    const selectReasoning = (index) => {
      draft.reasoningEffort = reasoningOptions[index];
      closeReasoningMenu();
    };

    const onReasoningKeydown = (event) => {
      if (event.key === 'Escape' && reasoningOpen.value) {
        event.preventDefault();
        event.stopPropagation();
        closeReasoningMenu();
        return;
      }
      if (!['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(event.key)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      if (!reasoningOpen.value) {
        openReasoningMenu();
        if (event.key !== 'Home' && event.key !== 'End') {
          return;
        }
      } else if (event.key === 'Enter' || event.key === ' ') {
        selectReasoning(activeReasoningIndex.value);
        return;
      }
      const last = reasoningOptions.length - 1;
      if (event.key === 'Home') {
        activeReasoningIndex.value = 0;
      } else if (event.key === 'End') {
        activeReasoningIndex.value = last;
      } else {
        activeReasoningIndex.value = Math.max(0, Math.min(last,
          activeReasoningIndex.value + (event.key === 'ArrowDown' ? 1 : -1)));
      }
      nextTick(revealActiveReasoning);
    };

    // Host blur can precede an option click; only actual outside interactions dismiss the menu.
    const onOutsideInteraction = (event) => {
      if (!reasoningTrigger.value?.contains(event.target) && !reasoningMenu.value?.contains(event.target)) {
        closeReasoningMenu();
      }
    };

    const onViewportScroll = (event) => {
      if (!reasoningMenu.value?.contains(event.target)) {
        positionReasoningMenu();
      }
    };

    const confirmSettings = () => {
      if (!dialog.value?.reportValidity()) {
        return;
      }
      emit('confirm', {
        temperature: draft.temperature,
        topP: draft.topP,
        maxTokens: draft.maxTokens === '' ? 8192 : draft.maxTokens,
        reasoningEffort: draft.reasoningEffort
      });
    };

    const onKeydown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        if (reasoningOpen.value) {
          closeReasoningMenu();
        } else {
          emit('close');
        }
      } else if (event.key === 'Tab') {
        closeReasoningMenu();
        const controls = [...dialog.value.querySelectorAll('button, input')];
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };

    onMounted(() => {
      dialog.value?.querySelector('input')?.focus();
      document.addEventListener('mousedown', onOutsideInteraction);
      document.addEventListener('focusin', onOutsideInteraction);
      window.addEventListener('resize', positionReasoningMenu);
      document.addEventListener('scroll', onViewportScroll, true);
    });
    onBeforeUnmount(() => {
      document.removeEventListener('mousedown', onOutsideInteraction);
      document.removeEventListener('focusin', onOutsideInteraction);
      window.removeEventListener('resize', positionReasoningMenu);
      document.removeEventListener('scroll', onViewportScroll, true);
      nextTick(() => {
        if (previousFocus?.isConnected) {
          previousFocus.focus();
        }
      });
    });

    return {
      dialog, draft, maxSafeInteger, samplingParameters, reasoningOptions, rangeProgress, confirmSettings, onKeydown,
      reasoningTrigger, reasoningMenu, reasoningOpen, activeReasoningIndex, reasoningMenuStyle,
      toggleReasoningMenu, closeReasoningMenu, selectReasoning, onReasoningKeydown
    };
  }
};
</script>

<style scoped>
.model-parameter-overlay {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.4);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.model-parameter-dialog {
  display: flex;
  flex-direction: column;
  width: 640px;
  max-width: 100%;
  max-height: 100%;
  margin: 0;
  overflow: hidden;
  background: #fff;
  color: #333;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(24, 30, 48, 0.2);
}

.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 24px 16px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.dialog-heading {
  min-width: 0;
  overflow-wrap: anywhere;
}

.dialog-heading h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.5;
}

.model-identity {
  margin: 5px 0 0;
  color: #888;
  font-size: 12px;
  line-height: 1.5;
}

.dialog-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  flex-shrink: 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #888;
  cursor: pointer;
}

.dialog-close:hover {
  background: #f5f5f5;
  color: #333;
}

.dialog-body {
  min-height: 0;
  padding: 16px 24px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.parameter-field {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  align-items: center;
  gap: 24px;
}

.parameter-field + .parameter-field {
  margin-top: 14px;
}

.parameter-description,
.parameter-control {
  min-width: 0;
}

.parameter-description {
  overflow-wrap: anywhere;
}

.parameter-field label {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
}

.field-hint {
  margin: 4px 0 0;
  color: #888;
  font-size: 12px;
  line-height: 1.6;
}

.token-input {
  position: relative;
}

.token-input input,
.reasoning-trigger,
.sampling-value {
  width: 100%;
  height: 36px;
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fff;
  color: #333;
  font-family: inherit;
  font-size: 13px;
}

.reasoning-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  text-align: left;
  cursor: pointer;
}

.reasoning-trigger svg {
  flex-shrink: 0;
}

.reasoning-menu {
  position: fixed;
  z-index: 2001;
  box-sizing: border-box;
  padding: 4px;
  overflow-y: auto;
  overscroll-behavior: contain;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fff;
  color: #333;
  box-shadow: 0 6px 20px rgba(24, 30, 48, 0.16);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 13px;
  scrollbar-width: thin;
  scrollbar-color: #c7ccdc #f5f6fa;
}

.reasoning-menu::-webkit-scrollbar {
  width: 6px;
}

.reasoning-menu::-webkit-scrollbar-track {
  background: #f5f6fa;
}

.reasoning-menu::-webkit-scrollbar-thumb {
  border-radius: 3px;
  background: #c7ccdc;
}

.reasoning-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 34px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.reasoning-option.is-active {
  background: #f0f2ff;
}

.reasoning-option.is-selected {
  color: #596bda;
  font-weight: 500;
}

.token-input input {
  padding-right: 72px;
}

.token-input span {
  position: absolute;
  top: 50%;
  right: 28px;
  transform: translateY(-50%);
  color: #999;
  font-size: 12px;
  pointer-events: none;
}

.token-input input::placeholder {
  color: #999;
}

.sampling-control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 88px;
  align-items: center;
  gap: 16px;
}

.range-control {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 10px;
}

.range-limit {
  flex-shrink: 0;
  color: #888;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.sampling-value {
  background: #f8f9ff;
  color: #596bda;
  font-variant-numeric: tabular-nums;
}

.parameter-range {
  display: block;
  appearance: none;
  -webkit-appearance: none;
  flex: 1;
  min-width: 0;
  width: 0;
  height: 6px;
  margin: 0 2px;
  border-radius: 6px;
  background: linear-gradient(to right, #667eea var(--range-progress), #e9ecf5 var(--range-progress));
  cursor: pointer;
}

.parameter-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: #667eea;
  box-shadow: 0 1px 4px rgba(63, 80, 175, 0.3);
}

.parameter-range::-moz-range-thumb {
  width: 12px;
  height: 12px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: #667eea;
  box-shadow: 0 1px 4px rgba(63, 80, 175, 0.3);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 24px;
  border-top: 1px solid #eee;
  flex-shrink: 0;
}

.dialog-button {
  padding: 8px 24px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
}

.cancel-button {
  background: #fff;
  color: #666;
}

.cancel-button:hover {
  background: #f5f5f5;
}

.confirm-button {
  border-color: #667eea;
  background: #667eea;
  color: #fff;
}

.confirm-button:hover {
  border-color: #596bda;
  background: #596bda;
}

.token-input input:focus,
.reasoning-trigger:focus,
.sampling-value:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.12);
}

.dialog-close:focus-visible,
.dialog-button:focus-visible,
.parameter-range:focus-visible {
  outline: 2px solid #667eea;
  outline-offset: 3px;
}

@media (max-width: 480px) {
  .model-parameter-overlay {
    padding: 12px;
  }

  .dialog-header,
  .dialog-body,
  .dialog-footer {
    padding-left: 18px;
    padding-right: 18px;
  }

  .parameter-field {
    grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
    gap: 12px;
  }

  .sampling-control {
    grid-template-columns: minmax(0, 1fr) 62px;
    gap: 8px;
  }

  .range-control {
    gap: 6px;
  }

  .sampling-value {
    padding: 8px 6px;
  }

  .token-input input {
    padding-left: 8px;
    padding-right: 56px;
  }

  .token-input span {
    right: 20px;
    font-size: 10px;
  }
}
</style>
