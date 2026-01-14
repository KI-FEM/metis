<script setup lang="ts">
  import type {components} from '@/types_api'

  import {useI18n} from 'vue-i18n'

  const { source, num } = defineProps<{
    /**
     * The source object containing label and other metadata.
     */
    source: components['schemas']['Source'];
    /**
     * The index number of the source, used for display.
     */
    num: number;
    /**
     * Optional flag to highlight the source.
     */
    highlighted?: boolean;
  }>()
  const { t } = useI18n()
  
  function getTitle(source: components['schemas']['Source']): string {
    if (!source || !source.title) {
      return t('unknownSource');
    }
    const label = source.title || t('unknownSource');
    const limit = 64; // Character limit for the label
    return label.length > limit ? label.slice(0, limit - 3) + '...' : label;
  }

  function getAuthorNames(source: components['schemas']['Source']): string {
    if (!source || !source.authors) {
      return t('unknownAuthor');
    }
    const authorList = source.authors;
    if (authorList.length > 2) {
      return `${authorList[0]} et al.`;
    }
    return authorList.join(', ');
  }

  function getPublicationYear(source: components['schemas']['Source']): string {
    if (!source || !source.year) {
      return t('unknownYear');
    }
    return source.year.toString();
  }
</script>

<template>
  <v-card :variant="highlighted ? 'outlined' : 'tonal'">
    <v-card-text>
      <div class="text-body-2 text-secondary mb-1">
        {{ `#${num}` }}
      </div>
      <!-- <v-skeleton-loader boilerplate type="card" /> -->
      <div class="text-body-2">
        {{ getTitle(source) }}
      </div>
      <div class="text-caption text-secondary">
        {{ getAuthorNames(source) }}
      </div>
      <div class="text-caption text-secondary">
        {{ getPublicationYear(source) }}
      </div>
    </v-card-text>
  </v-card>
</template>