<template>
  <div class="template-paper" aria-hidden="true">
    <img v-if="thumbnail && !imageFailed" :src="thumbnail" alt="" @error="imageFailed = true" />
    <div v-else class="template-paper-text">
      <p
        v-for="(line, index) in lines"
        :key="index"
        :class="{ 'paper-heading': line.heading, 'paper-centered': line.centered }"
      >{{ line.text }}</p>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    entry: { type: Object, required: true },
    thumbnail: { type: String, default: '' }
  },
  data: () => ({ imageFailed: false }),
  computed: {
    lines() {
      return this.entry.coverLines?.length
        ? this.entry.coverLines
        : [{ text: this.entry.name, heading: true, centered: true }];
    }
  }
};
</script>

<style scoped>
.template-paper {
  position: relative;
  aspect-ratio: 210 / 297;
  overflow: hidden;
  background: #fff;
  color: #2a3040;
  border: 1px solid #e5e8ef;
  box-shadow: 0 4px 13px #28325417;
  container-type: inline-size;
}
.template-paper img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.template-paper-text {
  padding: 17% 12%;
}
.template-paper p {
  margin: 0 0 7%;
  font-family: 'Songti SC', SimSun, Georgia, serif;
  font-size: 11px;
  font-size: clamp(8px, 6cqw, 12px);
  line-height: 1.35;
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.template-paper .paper-heading {
  font-weight: 700;
  font-size: 14px;
  font-size: clamp(11px, 9cqw, 19px);
}
.paper-centered {
  text-align: center;
}
</style>
