<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">元数据管理</h1>
      <p class="page-subtitle">管理数据表、字段、术语和主题等元数据信息</p>
    </div>

    <!-- 导航标签 -->
    <div class="tabs tabs-boxed mb-6">
      <RouterLink 
        to="/metadata/tables" 
        class="tab"
        :class="{ 'tab-active': $route.name === 'MetadataTables' }"
      >
        表管理
      </RouterLink>
      <RouterLink 
        to="/metadata/fields" 
        class="tab"
        :class="{ 'tab-active': $route.name === 'MetadataFields' }"
      >
        字段管理
      </RouterLink>
      <RouterLink 
        to="/metadata/glossary" 
        class="tab"
        :class="{ 'tab-active': $route.name === 'MetadataGlossary' }"
      >
        术语管理
      </RouterLink>
      <RouterLink 
        to="/metadata/themes" 
        class="tab"
        :class="{ 'tab-active': $route.name === 'MetadataThemes' }"
      >
        主题管理
      </RouterLink>
    </div>

    <!-- 子路由内容 -->
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>