<script setup lang="ts">
  import { ref, watch, nextTick, watchEffect } from 'vue'
  import type { components } from "@/types_api";
  import { useRoute } from "vue-router";
  import SourceDisplay from './SourceDisplay.vue';
  import SourceInfoDialog from './dialogs/SourceInfoDialog.vue';

  const { citations, timestamp } = defineProps<{
    /**
     * An array of citations, each containing a source object. The order defines the display order.
     */
    citations: components['schemas']['Source'][];
    /**
     * The timestamp of the message to which these citations belong, used for matching with route hash.
     */
    timestamp: string;
  }>();

  const route = useRoute();
  const showSources = ref(false);
  const selectedSource = ref<number | null>(null);
  const showSourceInfo = ref(false);

  watch(
    () => route.hash,
    (hash) => {
      // Check if the hash matches the pattern #source-<timestamp>-<id>
      const match = hash.match(/^#source-(\d+)-(\d+)$/);
      if (match) {
        const routeTimestamp = parseInt(match[1], 10);
        if (routeTimestamp !== new Date(timestamp).getTime()) return; // Ensure the timestamp matches the current message
        const id = parseInt(match[2], 10);
        if (!isNaN(id)) {
          selectedSource.value = id;
          showSources.value = true; // Show sources if a source ID is provided
          //document.getElementById(`source-${timestamp}-${id}`)?.click(); // TODO: Still some issues with focus when clicking citation links, also selected source is not propagated to slide-group
        }
      } else {
        selectedSource.value = null; // Reset selection if no valid source ID
      }
    },
    { immediate: true }
  );

  watch(showSourceInfo, () => {
    if (!showSourceInfo.value) {
      selectedSource.value = null; // Reset selection when closing the dialog
    }
  });

  watchEffect(async () => {
    if (showSources.value) await nextTick().then(scrollToBottom);
  });

  function scrollToBottom() {
    const scrollContainer = document.getElementsByClassName('v-main__scroller')[0]
    scrollContainer?.scrollTo({top: scrollContainer.scrollHeight, behavior: 'smooth'})
  }

  function selectSource(index: number) {
    selectedSource.value = index;
    showSourceInfo.value = true;
  }
</script>

<template>
  <div class="d-flex flex-row justify-around align-center ga-1" :class="{'mb-1': showSources}">
    <v-divider />
    <div>
      <v-btn class="mx-4"
             color="secondary" 
             :prepend-icon="!showSources ? 'fas fa-chevron-down' : 'fas fa-chevron-up'"
             size="small"
             variant="text"
             @click="showSources = !showSources">
        {{ showSources ? $t("hideSources") : $t("showSources", { num: citations.length }) }}
      </v-btn>
    </div>
    <v-divider />
  </div>
  <SourceInfoDialog v-if="selectedSource"
                    v-model="showSourceInfo"
                    :source="citations[selectedSource-1]" />
  <v-slide-group v-show="showSources"
                 id="source-slide-group"
                 v-model="selectedSource"
                 center-active>
    <v-slide-group-item v-for="(source, index) in citations"
                        :key="index"
                        :value="index + 1">
      <SourceDisplay class="me-4"
                     :highlighted="selectedSource === index + 1"
                     max-height="200"
                     max-width="180"
                     :num="Number(index) + 1"
                     :source="source"
                     @click="selectSource(index + 1)" />
    </v-slide-group-item>
  </v-slide-group>
</template>