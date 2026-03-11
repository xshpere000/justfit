<template>
  <div class="banner-section">
    <el-carousel :interval="5000" trigger="click" :height="height" arrow="always">
      <el-carousel-item v-for="feature in features" :key="feature.title">
        <div class="banner-item" :class="'banner--' + feature.color">
          <div class="banner-content">
            <div class="banner-text">
              <div class="banner-tag">核心功能</div>
              <h1 class="banner-title">{{ feature.title }}</h1>
              <p class="banner-desc">{{ feature.description }}</p>
              <el-button type="primary" round class="banner-btn" size="small" @click="$emit('start-task')">
                立即体验
              </el-button>
            </div>
            <div class="banner-icon-bg">
              <el-icon><component :is="feature.icon" /></el-icon>
            </div>
          </div>
        </div>
      </el-carousel-item>
    </el-carousel>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Feature {
  icon: string
  title: string
  description: string
  color: string
}

interface Props {
  height?: string
}

interface Emits {
  (e: 'start-task'): void
}

withDefaults(defineProps<Props>(), {
  height: '180px'
})

defineEmits<Emits>()

const features: Feature[] = [
  {
    icon: 'Monitor',
    title: '僵尸虚机检测',
    description: '通过智能算法识别长期低负载、长期关机或无流量的僵尸虚拟机，释放闲置资源。',
    color: 'orange'
  },
  {
    icon: 'TrendCharts',
    title: '资源规格优化 (RightSizing)',
    description: '基于历史负载数据，精准分析虚拟机资源配置合理性，建议升降配方案。',
    color: 'blue'
  },
  {
    icon: 'Coin',
    title: '潮汐模式分析',
    description: '挖掘业务资源使用的周期性规律（日/周/月），助力错峰调度与弹性伸缩。',
    color: 'purple'
  },
  {
    icon: 'FirstAidKit',
    title: '云平台健康体检',
    description: '全方位评估计算、存储、网络资源的健康状态，识别潜在风险点。',
    color: 'green'
  }
]
</script>

<style scoped lang="scss">
.banner-section {
  :deep(.el-carousel__indicators) {
    bottom: 20px;
  }

  :deep(.el-carousel__button) {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .banner-item {
    height: 100%;
    position: relative;
    overflow: hidden;
    background-size: cover;
    background-position: center;

    &.banner--orange {
      background: linear-gradient(120deg, #1c2438 0%, #3e2820 100%);
    }
    &.banner--blue {
      background: linear-gradient(120deg, #1c2438 0%, #1e3a5f 100%);
    }
    &.banner--purple {
      background: linear-gradient(120deg, #1c2438 0%, #382046 100%);
    }
    &.banner--green {
      background: linear-gradient(120deg, #1c2438 0%, #1e4238 100%);
    }

    .banner-content {
      height: 100%;
      max-width: 1366px;
      margin: 0 auto;
      padding: 0 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: white;
    }

    .banner-text {
      flex: 1;
      z-index: 2;
      padding-left: 36px;

      .banner-tag {
        display: inline-block;
        padding: 2px 8px;
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(4px);
        border-radius: 4px;
        font-size: 12px;
        margin-bottom: 8px;
        letter-spacing: 1px;
      }

      .banner-title {
        font-size: 24px;
        font-weight: 700;
        margin: 0 0 8px 0;
        letter-spacing: 1px;
      }

      .banner-desc {
        font-size: 13px;
        line-height: 1.5;
        opacity: 0.8;
        max-width: 600px;
        margin-bottom: 16px;
      }

      .banner-btn {
        padding: 8px 24px;
        font-weight: 600;
      }
    }

    .banner-icon-bg {
      font-size: 180px;
      opacity: 0.1;
      position: absolute;
      right: 100px;
      bottom: -40px;
      transform: rotate(-15deg);
      z-index: 1;
      color: white;
    }
  }
}
</style>
