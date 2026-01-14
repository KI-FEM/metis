<script setup lang="ts">
  import { useCitationBotStore } from "@/stores/citationBot";
  import { ref } from "vue";
  import { useI18n } from "vue-i18n";

  const { t } = useI18n();
  const citationBotStore = useCitationBotStore();

  const editing = ref({
    title: false,
    task: false,
    deadlines: false,
    additionalInfo: false,
  });

  const newDeadlineName = ref("");
  const newDeadlineDate = ref("");

  function addDeadline() {
    if (newDeadlineName.value && newDeadlineDate.value) {
      citationBotStore.addDeadline({
        name: newDeadlineName.value,
        date: newDeadlineDate.value,
      });
      // Felder leeren nach dem Hinzufügen
      newDeadlineName.value = "";
      newDeadlineDate.value = "";
    }
  }

  function removeDeadline(index: number) {
    citationBotStore.removeDeadline(index);
  }

  function saveDeadlines() {
    // Wenn Felder ausgefüllt sind, neue Deadline hinzufügen
    if (newDeadlineName.value && newDeadlineDate.value) {
      citationBotStore.addDeadline({
        name: newDeadlineName.value,
        date: newDeadlineDate.value,
      });
    }
    editing.value.deadlines = false;
    newDeadlineName.value = "";
    newDeadlineDate.value = "";
  }
</script>

<template>
  <v-card class="pa-4" rounded="lg">
    <v-card-title class="d-flex justify-space-between align-center">
      <span>{{ t("citationBot.sidebar.title") }}</span>
    </v-card-title>
    <v-card-text>
      <div v-if="!editing.title">
        <p class="context-text">
          <v-icon class="mr-2" color="success" icon="far fa-check-circle" />
          {{ citationBotStore.context.title }}
        </p>
        <v-btn class="edit-btn"
               icon="far fa-pen-to-square"
               size="small"
               variant="text"
               @click="editing.title = true" />
      </div>
      <div v-else>
        <v-textarea auto-grow
                    class="context-textarea"
                    density="comfortable"
                    :model-value="citationBotStore.context.title"
                    rows="3"
                    variant="outlined"
                    @update:model-value="(value) => citationBotStore.updateTitle(value)" />
        <v-btn class="mt-2" 
               color="primary"
               @click="editing.title = false">
          {{ t("citationBot.sidebar.save") }}
        </v-btn>
      </div>
    </v-card-text>

    <v-divider class="my-4" />

    <v-card-title class="d-flex justify-space-between align-center">
      <span>{{ t("citationBot.sidebar.task") }}</span>
    </v-card-title>
    <v-card-text>
      <div v-if="!editing.task">
        <p class="context-text">
          <v-icon class="mr-2" icon="far fa-circle" />
          {{ citationBotStore.context.task }}
        </p>
        <v-btn class="edit-btn"
               icon="far fa-pen-to-square"
               size="small"
               variant="text"
               @click="editing.task = true" />
      </div>
      <div v-else>
        <v-textarea auto-grow
                    class="context-textarea"
                    density="comfortable"
                    :model-value="citationBotStore.context.task"
                    rows="3"
                    variant="outlined"
                    @update:model-value="(value) => citationBotStore.updateTask(value)" />
        <v-btn class="mt-2" 
               color="primary"
               @click="editing.task = false">
          {{ t("citationBot.sidebar.save") }}
        </v-btn>
      </div>
    </v-card-text>

    <v-divider class="my-4" />

    <v-card-title class="d-flex justify-space-between align-center">
      <span>{{ t("citationBot.sidebar.goalsAndDeadlines") }}</span>
    </v-card-title>
    <v-card-text>
      <div v-if="!editing.deadlines">
        <div v-if="citationBotStore.context.deadlines.length > 0">
          <div v-for="(deadline, index) in citationBotStore.context.deadlines"
               :key="index"
               class="deadline-item mb-2">
            <v-icon class="mr-2" color="success" icon="far fa-check-circle" />
            <span class="deadline-name">{{ deadline.name }}:</span>
            <span class="deadline-date">{{ deadline.date }}</span>
          </div>
        </div>
        <div v-else class="text-muted">
          <v-icon class="mr-2" icon="far fa-circle" />
          {{ t("citationBot.sidebar.noDeadlines") }}
        </div>
        <v-btn class="edit-btn"
               icon="far fa-pen-to-square"
               size="small"
               variant="text"
               @click="editing.deadlines = true" />
      </div>
      <div v-else>
        <div v-for="(deadline, index) in citationBotStore.context.deadlines"
             :key="index"
             class="d-flex align-center ga-2 mb-3">
          <v-text-field dense
                        density="comfortable"
                        hide-details
                        class="deadline-input"
                        :label="t('citationBot.sidebar.name')"
                        :model-value="deadline.name"
                        variant="outlined"
                        @update:model-value="
                          (value) =>
                            citationBotStore.updateDeadline(index, {
                              ...deadline,
                              name: value,
                            })
                        " />
          <v-text-field dense
                        hide-details
                        :label="t('citationBot.sidebar.date')"
                        density="comfortable"
                        :model-value="deadline.date"
                        class="deadline-input"
                        type="date"
                        variant="outlined"
                        @update:model-value="
                          (value) =>
                            citationBotStore.updateDeadline(index, {
                              ...deadline,
                              date: value,
                            })
                        " />
          <v-btn color="error"
                 icon="far fa-trash-can"
                 size="small"
                 variant="text"
                 @click="removeDeadline(index)" />
        </div>
        <v-divider class="my-3" />
        <div class="d-flex align-center ga-2 mb-3">
          <v-text-field v-model="newDeadlineName"
                        class="deadline-input"
                        dense
                        density="comfortable"
                        hide-details
                        :label="t('citationBot.sidebar.newMilestone')"
                        variant="outlined" />
          <v-text-field v-model="newDeadlineDate"
                        class="deadline-input"
                        dense
                        density="comfortable"
                        hide-details
                        :label="t('citationBot.sidebar.date')"
                        type="date"
                        variant="outlined" />
          <v-btn color="primary" 
                 :disabled="!newDeadlineName || !newDeadlineDate" 
                 icon="fas fa-plus"
                 size="small"
                 variant="text"
                 @click="addDeadline" />
        </div>
        <v-btn class="mt-2" 
               color="primary"
               @click="saveDeadlines">
          {{ t("citationBot.sidebar.save") }}
        </v-btn>
      </div>
    </v-card-text>

    <v-divider class="my-4" />

    <v-card-title class="d-flex justify-space-between align-center">
      <span>{{ t("citationBot.sidebar.additionalInfo") }}</span>
    </v-card-title>
    <v-card-text>
      <div v-if="!editing.additionalInfo">
        <p class="context-text">
          <v-icon class="mr-2" icon="far fa-circle" />
          {{ citationBotStore.context.additionalInfo }}
        </p>
        <v-btn class="edit-btn"
               icon="far fa-pen-to-square"
               size="small"
               variant="text"
               @click="editing.additionalInfo = true" />
      </div>
      <div v-else>
        <v-textarea auto-grow
                    class="context-textarea"
                    density="comfortable"
                    :model-value="citationBotStore.context.additionalInfo"
                    rows="3"
                    variant="outlined"
                    @update:model-value="
                      (value) => citationBotStore.updateAdditionalInfo(value)
                    " />
        <v-btn class="mt-2" 
               color="primary"
               @click="editing.additionalInfo = false">
          {{ t("citationBot.sidebar.save") }}
        </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.edit-btn {
  position: absolute;
  top: 10px;
  right: 10px;
}

.v-card-text {
  position: relative;
}

.context-text {
  margin-bottom: 0;
  line-height: 1.5;
  min-height: 24px;
}

.context-textarea {
  margin-bottom: 8px;
}

.deadline-item {
  display: flex;
  align-items: center;
  padding: 8px 0;
}

.deadline-name {
  font-weight: 500;
  margin-right: 8px;
}

.deadline-date {
  color: rgba(var(--v-theme-on-surface), 0.7);
}

.deadline-input {
  flex: 1;
}

.text-muted {
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-style: italic;
}
</style>
