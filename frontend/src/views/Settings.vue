<template>
  <div class="settings-page">
    <el-card>
      <template #header>
        <span>系统设置</span>
      </template>

      <el-empty description="系统设置功能开发中">
        <el-button type="primary" @click="goBack">返回</el-button>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goBack() {
  router.back()
}
</script>

<style scoped lang="scss">
.settings-page {
  .el-empty {
    padding: $spacing-xl 0;
  }
}
</style>
