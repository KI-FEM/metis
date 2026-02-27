<script setup lang="ts">
  import {useI18n} from 'vue-i18n'

  import DialogCloseButton from '@/components/buttons/DialogCloseButton.vue'
  import type {components} from '@/types_api.ts'

  const {source} = defineProps<{
    /**
     * The source object containing label and other metadata.
     */
    source: components['schemas']['Source'];
  }>()

  const showDialog = defineModel<boolean>({default: false})

  const {t} = useI18n()

  function getAuthors(source: components['schemas']['Source']): string {
    if (!source.additional_metadata || !source.additional_metadata['authors']) {
      return t('unknownAuthor')
    }
    const authors = source.additional_metadata['authors'] as { name: string }[]
    return authors.map(author => author.name).join(', ')
  }

  function getPublicationYear(source: components['schemas']['Source']): string {
    if (!source.additional_metadata || !source.additional_metadata['publication_year']) {
      return t('unknownYear')
    }
    return source.additional_metadata['publication_year'].toString()
  }

  const getLanguage = (locale: string | unknown): string => {
    if (typeof(locale) === "string") return t('languageLabel' + locale[0].toUpperCase() + locale[1])
    return t('unknownLanguage')
  }
</script>

<template>
  <v-dialog v-model="showDialog" max-width="700">
    <v-card>
      <v-card-item>
        <v-card-title class="d-flex align-center">
          {{ source.label || t('unknownSource') }}
          <DialogCloseButton class="ms-auto" @click="showDialog = false" />
        </v-card-title>
        <v-card-subtitle>
          {{ getAuthors(source) }}
        </v-card-subtitle>
      </v-card-item>
      <v-card-text>
        <div class="d-flex flex-row ga-2 justify-space-between mb-2">
          <v-skeleton-loader boilerplate class="w-50" type="card" />
          <div class="w-50">
            <v-card class="h-100 w-100 pa-2" variant="outlined">
              <v-card-title>
                {{ $t('sourceAdditionalInfosLabel') }}
              </v-card-title>
              <v-card-text>
                <ul class="list-disc pl-4">
                  <li>{{ $t('sourcePublicationYearLabel') }}: {{ getPublicationYear(source) }}</li>
                  <li>{{ $t('sourceOriginalLanguageLabel') }} : {{ getLanguage(source.additional_metadata['language']) }}</li>
                </ul>
              </v-card-text>
            </v-card>
          </div>
        </div>
        <span class="text-h7">{{ $t('sourceChunkLabel') }}</span>
        <v-card class="mt-2 overflow-y-auto text-pre-wrap" style="max-height: 300px;" variant="outlined">
          <v-card-text>
            <span class="text-body-2">
              {{ source.chunk }}
            </span> 
          </v-card-text>
        </v-card>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

