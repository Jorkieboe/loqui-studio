import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNavbarStore = defineStore('navbar', () => {
  const actionLabel = ref('')
  const actionFn = ref(null)
  const actionActive = ref(false)
  const actionTimeout = ref(null)

  function setAction(label, fn) {
    actionLabel.value = label
    actionFn.value = fn
  }

  function clearAction() {
    actionLabel.value = ''
    actionFn.value = null
  }

  function doAction() {
    actionActive.value = true
    actionFn.value()
    
    if(actionTimeout) clearTimeout(actionTimeout)

    actionTimeout.value = setTimeout(()=>{
      actionActive.value = false
    }, 500)
  }

  return { actionLabel, actionFn, actionActive, setAction, clearAction, doAction}
})
