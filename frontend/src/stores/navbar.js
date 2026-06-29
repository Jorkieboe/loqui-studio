import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNavbarStore = defineStore('navbar', () => {
  const actionLabel = ref('')
  const actionFn = ref(null)

  function setAction(label, fn) {
    actionLabel.value = label
    actionFn.value = fn
  }

  function clearAction() {
    actionLabel.value = ''
    actionFn.value = null
  }

  return { actionLabel, actionFn, setAction, clearAction }
})
