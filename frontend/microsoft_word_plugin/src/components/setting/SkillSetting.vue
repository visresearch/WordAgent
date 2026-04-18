<template>
  <div class="mcp-setting-container">
    <div class="section-header">
      <img class="section-icon" :src="iconSkill" alt="Skill 图标" />
      <div class="section-title-group">
        <h2 class="section-title">
          Skill 管理
        </h2>
        <p class="section-subtitle">
          上传包含 SKILL.md 的 zip 压缩包，系统会自动解压到本地 skills 目录
        </p>
      </div>
    </div>

    <div class="toolbar">
      <button class="btn-add-server" :disabled="uploading" @click="openUploadDialog">
        <svg
          width="14"
          height="14"
          viewBox="0 0 16 16"
          fill="currentColor"
        >
          <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z" />
        </svg>
        {{ uploading ? '上传中...' : '上传 Skill 压缩包' }}
      </button>
      <input
        ref="fileInputRef"
        type="file"
        accept=".zip,application/zip"
        class="hidden-file-input"
        @change="onFileChange"
      />
      <span class="toolbar-tip">仅支持 zip，且压缩包中需包含 SKILL.md</span>
    </div>

    <p v-if="message" :class="['status-message', messageType === 'success' ? 'success' : 'error']">
      {{ message }}
    </p>

    <div v-if="loading" class="empty-state">
      <p>正在加载 Skill 列表...</p>
    </div>

    <div v-else-if="skills.length === 0" class="empty-state">
      <p>还没有 Skill，点击上方“上传 Skill 压缩包”开始配置。</p>
    </div>

    <div v-else class="server-list">
      <div
        v-for="skill in skills"
        :key="skill.folder"
        class="server-card"
      >
        <div class="server-header">
          <div class="server-info">
            <div class="skill-text-group">
              <span class="server-name">{{ skill.name || '未命名 Skill' }}</span>
              <span class="skill-meta">{{ skill.folder }}{{ skill.description ? ` - ${skill.description}` : '' }}</span>
            </div>
          </div>
          <div class="server-actions">
            <label class="switch switch-sm" title="启用/禁用 Skill">
              <input
                :checked="skill.enabled !== false"
                type="checkbox"
                :disabled="busyFolder === skill.folder"
                @change="toggleSkill(skill, $event)"
              />
              <span class="slider"></span>
            </label>
            <button
              class="action-btn delete"
              :disabled="busyFolder === skill.folder"
              title="删除"
              @click="removeSkillItem(skill)"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z" />
                <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { onMounted, ref } from 'vue';
import api from '../js/api.js';
import iconSkill from '../../assets/icons/skill.svg';

export default {
  name: 'SkillSetting',
  setup() {
    const loading = ref(false);
    const uploading = ref(false);
    const busyFolder = ref('');
    const skills = ref([]);
    const message = ref('');
    const messageType = ref('success');
    const fileInputRef = ref(null);

    const setMessage = (text, type = 'success') => {
      message.value = text;
      messageType.value = type;
      if (text) {
        setTimeout(() => {
          if (message.value === text) {
            message.value = '';
          }
        }, 2600);
      }
    };

    const loadSkills = async () => {
      loading.value = true;
      try {
        skills.value = await api.getSkills();
      } catch (error) {
        console.error('加载 skills 失败:', error);
        setMessage(error.message || '加载 skill 失败', 'error');
      } finally {
        loading.value = false;
      }
    };

    const openUploadDialog = () => {
      if (uploading.value) {
        return;
      }
      fileInputRef.value?.click();
    };

    const onFileChange = async (event) => {
      const file = event?.target?.files?.[0];
      if (!file) {
        return;
      }

      if (!file.name.toLowerCase().endsWith('.zip')) {
        setMessage('仅支持上传 zip 压缩包', 'error');
        event.target.value = '';
        return;
      }

      uploading.value = true;
      try {
        const result = await api.uploadSkillPackage(file);
        setMessage(result?.message || 'Skill 上传成功', 'success');
        await loadSkills();
      } catch (error) {
        console.error('上传 skill 失败:', error);
        setMessage(error.message || '上传 skill 失败', 'error');
      } finally {
        uploading.value = false;
        event.target.value = '';
      }
    };

    const toggleSkill = async (skill, event) => {
      const nextEnabled = !!event?.target?.checked;
      busyFolder.value = skill.folder;
      try {
        await api.setSkillEnabled(skill.folder, nextEnabled);
        skill.enabled = nextEnabled;
      } catch (error) {
        console.error('更新 skill 启用状态失败:', error);
        setMessage(error.message || '更新 skill 状态失败', 'error');
        event.target.checked = !nextEnabled;
      } finally {
        busyFolder.value = '';
      }
    };

    const removeSkillItem = async (skill) => {
      const confirmed = window.confirm(`确认删除 Skill: ${skill.name || skill.folder} ?`);
      if (!confirmed) {
        return;
      }

      busyFolder.value = skill.folder;
      try {
        await api.deleteSkill(skill.folder);
        setMessage('Skill 删除成功', 'success');
        skills.value = skills.value.filter((item) => item.folder !== skill.folder);
      } catch (error) {
        console.error('删除 skill 失败:', error);
        setMessage(error.message || '删除 skill 失败', 'error');
      } finally {
        busyFolder.value = '';
      }
    };

    onMounted(() => {
      loadSkills();
    });

    return {
      iconSkill,
      loading,
      uploading,
      busyFolder,
      skills,
      message,
      messageType,
      fileInputRef,
      openUploadDialog,
      onFileChange,
      toggleSkill,
      removeSkillItem
    };
  }
};
</script>

<style scoped>
.mcp-setting-container {
  width: 100%;
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

.toolbar {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-add-server {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  border-radius: 8px;
  background: #10b981;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 12px;
  cursor: pointer;
}

.btn-add-server:hover:not(:disabled) {
  background: #059669;
}

.btn-add-server:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.hidden-file-input {
  display: none;
}

.toolbar-tip {
  font-size: 12px;
  color: #6b7280;
}

.status-message {
  margin: 0 0 12px 0;
  font-size: 12px;
}

.status-message.success {
  color: #059669;
}

.status-message.error {
  color: #dc2626;
}

.empty-state {
  border: 1px dashed #d1d5db;
  border-radius: 10px;
  padding: 20px;
  color: #6b7280;
  font-size: 13px;
  text-align: center;
}

.server-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.server-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  background: #ffffff;
}

.server-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #f9fafb;
}

.server-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.skill-text-group {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.server-name {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
}

.skill-meta {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 620px;
}

.server-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  color: #666;
  transition: all 0.2s;
}

.action-btn:hover:not(:disabled) {
  background: #f5f5f5;
  color: #333;
}

.action-btn.delete:hover:not(:disabled) {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fecaca;
}

.action-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.3s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.switch input:checked + .slider {
  background-color: #667eea;
}

.switch input:checked + .slider:before {
  transform: translateX(20px);
}

.switch-sm {
  width: 36px;
  height: 20px;
}

.switch-sm .slider:before {
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
}

.switch-sm input:checked + .slider:before {
  transform: translateX(16px);
}
</style>
