window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data() {
    return {
      userAmount: paywall.amount,
      paywallAmount: paywall.amount,
      paywallMemo: paywall.memo,
      paywallDescription: paywall.description,
      paymentReq: null,
      redirectUrl: null,
      paymentDialog: {
        dismissMsg: null,
        checker: null
      }
    }
  },
  computed: {
    amount() {
      return this.paywallAmount > this.userAmount
        ? this.paywallAmount
        : this.userAmount
    }
  },
  methods: {
    cancelPayment() {
      this.paymentReq = null
      clearInterval(this.paymentDialog.checker)
      if (this.paymentDialog.dismissMsg) {
        this.paymentDialog.dismissMsg()
      }
    },
    createInvoice() {
      LNbits.api
        .request(
          'POST',
          `/paywall/api/v1/paywalls/invoice/${paywall.id}`,
          'filler',
          {
            amount: this.amount
          }
        )
        .then(response => {
          if (response.data) {
            this.paymentReq = response.data.payment_request.toUpperCase()
            this.paymentDialog.dismissMsg = Quasar.Notify.create({
              timeout: 0,
              message: 'Waiting for payment...'
            })

            this.paymentDialog.checker = setInterval(() => {
              LNbits.api
                .request(
                  'POST',
                  `/paywall/api/v1/paywalls/check_invoice/${paywall.id}`,
                  'filler',
                  {payment_hash: response.data.payment_hash}
                )
                .then(response => {
                  if (response.data) {
                    if (response.data.paid) {
                      this.cancelPayment()
                      this.redirectUrl = response.data.url
                      if (response.data.remembers) {
                        this.$q.localStorage.set(
                          `lnbits.paywall.${paywall.id}`,
                          response.data.url
                        )
                      }
                      Quasar.Notify.create({
                        type: 'positive',
                        message: 'Payment received!',
                        icon: null
                      })
                    }
                  }
                })
                .catch(LNbits.utils.notifyApiError)
            }, 2000)
          }
        })
        .catch(LNbits.utils.notifyApiError)
    }
  },
  created() {
    const url = this.$q.localStorage.getItem(`lnbits.paywall.${paywall.id}`)
    if (url) {
      this.redirectUrl = url
    }
  }
})
