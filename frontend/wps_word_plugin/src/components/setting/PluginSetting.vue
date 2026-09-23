<template>
  <div class="plugin-panel">
    <div v-if="message" :class="['plugin-message', messageError ? 'error' : 'success']">{{ message }}</div>

    <div v-if="loading" class="plugin-muted">{{ $t('plugin.loading') }}</div>
    <div v-for="plugin in plugins" :key="plugin.id" class="plugin-card">
      <div class="plugin-info">
        <strong>{{ plugin.name }}</strong>
        <p>{{ plugin.id === 'ocr' ? $t('plugin.ocrDescription') : plugin.description }}</p>
        <small>{{ plugin.package || plugin.source || plugin.id }}</small>
      </div>
      <button
        v-if="plugin.installed"
        class="plugin-button danger"
        :disabled="busy.includes(plugin.id)"
        @click="remove(plugin)"
      >{{ busy.includes(plugin.id) ? $t('plugin.removing') : $t('plugin.remove') }}</button>
      <button
        v-else
        class="plugin-button"
        :disabled="busy.includes(plugin.id)"
        @click="install(plugin.id)"
      >{{ busy.includes(plugin.id) ? $t('plugin.installing') : $t('plugin.install') }}</button>
    </div>

    <div class="plugin-custom">
      <h3>{{ $t('plugin.customTitle') }}</h3>
      <p>{{ $t('plugin.customHint') }}</p>
      <div class="plugin-form">
        <input v-model.trim="customSource" :placeholder="$t('plugin.packagePlaceholder')" @keyup.enter="installCustom" />
        <button class="plugin-button" :disabled="!customSource || customBusy" @click="installCustom">
          {{ customBusy ? $t('plugin.installing') : $t('plugin.installCustom') }}
        </button>
      </div>
      <div class="plugin-upload">
        <label class="plugin-button upload-button">
          {{ $t('plugin.uploadWheel') }}
          <input type="file" accept=".whl" :disabled="customBusy" @change="uploadWheel" />
        </label>
      </div>
    </div>

    <div v-if="selectedOperation" class="plugin-log">
      <strong>{{ $t('plugin.log') }} · {{ selectedOperation.pluginId }}</strong>
      <pre>{{ selectedOperation.logs.join('\n') }}</pre>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import api from '../js/api.js';
import { t } from '../../i18n/index.js';

const plugins = ref([]);
const busy = ref([]);
const operations = ref({});
const selectedId = ref('');
const customSource = ref('');
const customBusy = ref(false);
const loading = ref(true);
const message = ref('');
const messageError = ref(false);
const selectedOperation = computed(() => operations.value[selectedId.value]);
let timer;
let polling = false;

async function refresh() {
  try {
    const data = await api.getPlugins();
    plugins.value = data.plugins || [];
    busy.value = data.busy || [];
    for (const operation of data.operations || []) {
      operations.value[operation.id] = operation;
      if (!selectedId.value) selectedId.value = operation.id;
    }
  } catch (error) {
    message.value = error.message;
    messageError.value = true;
  } finally {
    loading.value = false;
  }
}

async function poll() {
  if (polling) return;
  polling = true;
  try {
    const active = Object.values(operations.value).filter(item => item.status === 'running');
    for (const operation of active) {
      const next = await api.getPluginOperation(operation.id);
      operations.value[operation.id] = next;
      if (next.status !== 'running') {
        messageError.value = next.status === 'failed';
        message.value = messageError.value ? next.error : t(next.action === 'install' ? 'plugin.installDone' : 'plugin.removeDone');
        customBusy.value = false;
        await refresh();
      }
    }
  } catch (error) {
    message.value = error.message;
    messageError.value = true;
  } finally {
    polling = false;
  }
}

function track(operation) {
  operations.value[operation.operationId] = {
    id: operation.operationId,
    pluginId: operation.pluginId,
    action: 'install',
    status: 'running',
    logs: []
  };
  selectedId.value = operation.operationId;
  busy.value = [...new Set([...busy.value, operation.pluginId])];
  message.value = '';
}

async function install(source) {
  try {
    track(await api.installPlugin(source));
  } catch (error) {
    message.value = error.message;
    messageError.value = true;
  }
}

async function installCustom() {
  if (!customSource.value || customBusy.value) return;
  customBusy.value = true;
  try {
    track(await api.installPlugin(customSource.value));
    customSource.value = '';
  } catch (error) {
    customBusy.value = false;
    message.value = error.message;
    messageError.value = true;
  }
}

async function uploadWheel(event) {
  const file = event.target.files?.[0];
  event.target.value = '';
  if (!file || customBusy.value) return;
  customBusy.value = true;
  try {
    track(await api.uploadPlugin(file));
  } catch (error) {
    customBusy.value = false;
    message.value = error.message;
    messageError.value = true;
  }
}

async function remove(plugin) {
  if (!confirm(t('plugin.removeConfirm', { name: plugin.name }))) return;
  try {
    const operation = await api.removePlugin(plugin.id);
    track(operation);
    operations.value[operation.operationId].action = 'remove';
  } catch (error) {
    message.value = error.message;
    messageError.value = true;
  }
}

onMounted(async () => {
  await refresh();
  timer = setInterval(poll, 800);
});
onUnmounted(() => clearInterval(timer));
</script>

<style scoped>
.plugin-panel { display: flex; flex-direction: column; gap: 14px; }
.plugin-card, .plugin-custom { display: flex; align-items: center; gap: 16px; padding: 16px; border: 1px solid #e5e7eb; border-radius: 10px; background: #fff; }
.plugin-info { flex: 1; min-width: 0; }
.plugin-info p, .plugin-custom p { margin: 5px 0; color: #737b86; font-size: 13px; line-height: 1.5; }
.plugin-info small { color: #949ca6; }
.plugin-button { border: 0; border-radius: 7px; background: #4f67c6; color: white; padding: 8px 14px; cursor: pointer; white-space: nowrap; }
.plugin-button.danger { background: #dc2626; }
.plugin-button:disabled { background: #cbd0d8; cursor: not-allowed; }
.plugin-custom { display: block; }
.plugin-custom h3 { font-size: 15px; margin: 0; }
.plugin-form { display: flex; gap: 8px; margin-top: 12px; }
.plugin-form input { flex: 1; min-width: 0; padding: 8px 10px; border: 1px solid #d4d9e1; border-radius: 7px; }
.plugin-upload { margin-top: 10px; }
.upload-button { display: inline-block; }
.upload-button input { display: none; }
.plugin-message { padding: 9px 12px; border-radius: 7px; color: #166534; background: #ecfdf3; }
.plugin-message.error { color: #b91c1c; background: #fef2f2; }
.plugin-muted { color: #737b86; }
.plugin-log { margin-top: 4px; }
.plugin-log pre { max-height: 260px; overflow: auto; padding: 12px; border-radius: 7px; color: #d1d5db; background: #1f2937; font-size: 11px; white-space: pre-wrap; }
</style>
