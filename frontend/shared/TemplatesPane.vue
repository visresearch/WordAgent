<template>
  <main class="templates-pane">
    <header class="templates-header">
      <div>
        <button v-if="selected" type="button" class="template-back" @click="closeDetails">
          <span aria-hidden="true">←</span> {{ $t('templates.back') }}
        </button>
        <h1 ref="heading" tabindex="-1">{{ selected?.name || $t('templates.title') }}</h1>
      </div>
      <button v-if="!selected" type="button" class="template-button" :disabled="loading" @click="loadTemplates">
        {{ $t('common.refresh') }}
      </button>
    </header>

    <section ref="body" class="templates-body" :aria-busy="loading">
      <p v-if="error" class="template-error" role="alert">{{ error }}</p>
      <p v-if="loading" class="template-state" role="status">{{ $t('common.loading') }}</p>

      <div v-else-if="selected" class="template-detail">
        <aside class="template-sidebar">
          <TemplateCover :entry="selected" :thumbnail="coverUrl(selected)" />
          <p class="template-original">{{ selected.originalName }}</p>
          <button
            v-if="!docxOnly || selected.format === 'docx'"
            type="button"
            class="template-button template-primary"
            :disabled="creating"
            @click="createCopy"
          >{{ $t(creating ? 'templates.creating' : 'templates.create') }}</button>
          <a class="template-button" :href="url(selected.id, 'file')">{{ $t('templates.download') }}</a>
        </aside>
        <section class="template-instructions">
          <header>
            <h2>{{ $t('templates.instructions') }}</h2>
            <button type="button" class="template-button" @click="copyInstructions">
              {{ $t(copied ? 'templates.copied' : 'templates.copy') }}
            </button>
          </header>
          <p v-if="created" class="template-success" role="status">{{ $t('templates.created') }}</p>
          <div class="template-markdown" v-html="instructionsHtml"></div>
        </section>
      </div>

      <div v-else-if="entries.length" class="template-grid">
        <button
          v-for="entry in entries"
          :key="entry.id"
          type="button"
          class="template-card"
          @click="openDetails(entry.id)"
        >
          <div class="template-card-cover">
            <TemplateCover :entry="entry" :thumbnail="coverUrl(entry)" />
          </div>
          <span class="template-card-name">{{ entry.name }}</span>
        </button>
      </div>

      <div v-else-if="!error" class="template-empty">
        <h2>{{ $t('templates.emptyTitle') }}</h2>
        <p>{{ $t('templates.emptyHint') }}</p>
        <blockquote>{{ $t('templates.example') }}</blockquote>
      </div>
    </section>
  </main>
</template>

<script>
import MarkdownIt from 'markdown-it';
import { templateEndpoint, templateRequest } from './documentTemplates.mjs';
import TemplateCover from './TemplateCover.vue';

const markdown = new MarkdownIt({ html: false }).disable(['image', 'link', 'autolink']);

export default {
  components: { TemplateCover },
  props: {
    baseUrl: { type: String, required: true },
    createDocument: { type: Function, required: true },
    docxOnly: { type: Boolean, default: false }
  },
  data: () => ({ entries: [], selected: null, error: '', loading: true, creating: false, copied: false, created: false }),
  computed: {
    instructionsHtml() {
      return this.selected ? markdown.render(this.selected.instructions) : '';
    }
  },
  mounted() {
    this.loadTemplates();
  },
  methods: {
    url(id, action) {
      return templateEndpoint(this.baseUrl, id, action);
    },
    coverUrl(entry) {
      return entry.hasThumbnail ? this.url(entry.id, 'cover') : '';
    },
    async fetchJson(id) {
      this.loading = true;
      this.error = '';
      try {
        const response = await templateRequest(this.url(id));
        return await response.json();
      } catch (error) {
        this.error = this.$t('templates.loadFailed', { error: error.message });
        return null;
      } finally {
        this.loading = false;
      }
    },
    async loadTemplates() {
      const entries = await this.fetchJson();
      if (entries) this.entries = entries;
    },
    async openDetails(id) {
      this.copied = false;
      this.created = false;
      this.selected = await this.fetchJson(id);
      if (!this.selected) return;
      await this.$nextTick();
      this.$refs.body.scrollTop = 0;
      this.$refs.heading.focus();
    },
    closeDetails() {
      this.selected = null;
      this.error = '';
    },
    async copyInstructions() {
      this.error = '';
      const instructions = this.selected.instructions;
      try {
        await navigator.clipboard.writeText(instructions);
        this.copied = true;
      } catch (error) {
        const node = document.createElement('textarea');
        node.value = instructions;
        node.style.position = 'fixed';
        node.style.opacity = '0';
        this.$el.appendChild(node);
        node.select();
        try {
          this.copied = document.execCommand('copy');
        } catch (error) {
          this.copied = false;
        } finally {
          node.remove();
        }
        if (!this.copied) this.error = this.$t('templates.copyFailed');
      }
    },
    async createCopy() {
      this.error = '';
      this.created = false;
      this.creating = true;
      const id = this.selected.id;
      try {
        await this.createDocument(id);
        if (this.selected?.id === id) this.created = true;
      } catch (error) {
        if (this.selected?.id === id) this.error = this.$t('templates.createFailed', { error: error.message });
      } finally {
        this.creating = false;
      }
    }
  }
};
</script>

<style scoped>
.templates-pane {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: var(--wps-viewport-height, 100vh);
  overflow: hidden;
  background: #f6f7fb;
  color: #25273b;
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.templates-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 19px clamp(16px, 4vw, 34px);
  background: #fff;
  border-bottom: 1px solid #e5e8f0;
}
.templates-header h1 {
  overflow-wrap: anywhere;
  margin: 0;
  font-size: 24px;
  line-height: 1.25;
  font-weight: 650;
}
.templates-body {
  flex: 1;
  overflow: auto;
  padding: 25px clamp(16px, 4vw, 34px);
}
.template-button,
.template-back,
.template-card {
  font: inherit;
  cursor: pointer;
}
.template-button {
  box-sizing: border-box;
  display: inline-block;
  padding: 6px 13px;
  flex-shrink: 0;
  border: 1px solid #dde0ec;
  border-radius: 7px;
  background: #fff;
  color: #494e70;
  text-decoration: none;
  text-align: center;
}
.template-button:hover,
.template-back:hover {
  background: #f0efff;
}
.template-button:disabled {
  opacity: .6;
  cursor: default;
}
.template-primary {
  background: #5b50c8;
  border-color: #5b50c8;
  color: #fff;
}
.template-primary:hover {
  background: #4d43b1;
}
.template-back {
  display: block;
  margin: 0 0 7px -5px;
  padding: 2px 5px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #534cae;
}
.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(145px, 1fr));
  gap: 18px;
}
.template-card {
  min-width: 0;
  padding: 0;
  overflow: hidden;
  text-align: left;
  color: inherit;
  border: 1px solid #e0e3ed;
  border-radius: 10px;
  background: #fff;
}
.template-card:hover {
  border-color: #8c82db;
  box-shadow: 0 5px 18px #5147ac1a;
}
.template-card-cover {
  display: grid;
  place-items: center;
  height: clamp(155px, 25vw, 208px);
  padding: 13px;
  box-sizing: border-box;
  background: #ebedf6;
}
.template-card-cover .template-paper {
  width: min(78%, 121px);
}
.template-card-name {
  display: block;
  padding: 11px 12px;
  overflow-wrap: anywhere;
  border-top: 1px solid #e5e7f1;
  font-weight: 600;
}
.template-detail {
  display: grid;
  grid-template-columns: minmax(145px, 195px) minmax(0, 1fr);
  align-items: start;
  gap: 22px;
}
.template-sidebar {
  display: grid;
  gap: 9px;
}
.template-original {
  margin: 4px 0;
  color: #59617b;
  overflow-wrap: anywhere;
}
.template-instructions {
  min-width: 0;
  border: 1px solid #e0e3ed;
  border-radius: 10px;
  background: #fff;
}
.template-instructions header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e8f0;
}
.template-instructions h2,
.template-empty h2 {
  margin: 0;
  font-size: 17px;
}
.template-markdown {
  padding: 15px 16px;
  overflow-wrap: anywhere;
  font-size: 14px;
  line-height: 1.65;
}
.template-markdown :deep(h1),
.template-markdown :deep(h2),
.template-markdown :deep(h3) {
  margin: 14px 0 6px;
  font-size: 16px;
}
.template-markdown :deep(p),
.template-markdown :deep(ol),
.template-markdown :deep(ul) {
  margin: 0 0 10px;
}
.template-markdown :deep(ol),
.template-markdown :deep(ul) {
  padding-left: 21px;
}
.template-markdown :deep(pre) {
  white-space: pre-wrap;
}
.template-markdown :deep(:first-child) {
  margin-top: 0;
}
.template-error,
.template-success {
  margin: 0 0 14px;
  padding: 9px 12px;
  border-radius: 7px;
  overflow-wrap: anywhere;
}
.template-error {
  color: #a12839;
  background: #fff0f1;
}
.template-success {
  margin: 12px 16px 0;
  color: #287250;
  background: #eff9f3;
}
.template-state,
.template-empty {
  margin: 8vh auto 0;
  text-align: center;
  color: #535b76;
}
.template-empty {
  max-width: 430px;
  padding: 26px;
  border: 1px dashed #c8cce2;
  border-radius: 12px;
  background: #fff;
}
.template-empty blockquote {
  margin: 16px 0 0;
  padding: 10px 12px;
  border-radius: 7px;
  background: #f1effd;
  color: #443b8d;
}
@media (max-width: 490px) {
  .template-detail { grid-template-columns: 1fr; }
  .template-sidebar .template-paper { max-width: 155px; }
}
</style>
