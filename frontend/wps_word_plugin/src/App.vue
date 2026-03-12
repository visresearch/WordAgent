<template>
  <RouterView />
</template>

<script>
import { ref, onMounted } from 'vue';
import ribbon from './components/ribbon.js';
export default {
  setup() {
    const message = ref('你好，wps加载项');
    onMounted(() => {
      window.ribbon = ribbon;
    });

    return {
      message
    };
  }
};
</script>

<style scoped></style>
