window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data() {
    return {
      userAmount: paywall.amount,
      paywallAmount: paywall.amount,
      paywallCurrency: paywall.currency,
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
    },
    formattedAmount() {
      if (this.paywallCurrency == 'sat') {
        return LNbits.utils.formatSat(this.amount) + ' sats'
      } else {
        return LNbits.utils.formatCurrency(
          Number(this.amount).toFixed(2),
          this.paywallCurrency
        )
      }
    }
  },
  methods: {
    cancelPayment() {
      this.paymentReq = null
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
            this.subscribeToPaymentWS(response.data.payment_hash)
          }
        })
        .catch(LNbits.utils.notifyApiError)
    },
    async getPaidPaywallData(paymentHash) {
      const {data} = await LNbits.api.request(
        'POST',
        `/paywall/api/v1/paywalls/check_invoice/${paywall.id}`,
        'filler',
        {payment_hash: paymentHash}
      )
      if (data && data.paid) {
        this.cancelPayment()
        this.redirectUrl = data.url
        if (data.remembers) {
          this.$q.localStorage.set(`lnbits.paywall.${paywall.id}`, data.url)
        }
      }
    },
    subscribeToPaymentWS(paymentHash) {
      try {
        const url = new URL(window.location)
        url.protocol = url.protocol === 'https:' ? 'wss' : 'ws'
        url.pathname = `/api/v1/ws/${paymentHash}`
        const ws = new WebSocket(url)
        ws.onmessage = async ({data}) => {
          const payment = JSON.parse(data)
          if (payment.pending === false) {
            Quasar.Notify.create({
              type: 'positive',
              message: 'Invoice Paid!'
            })
            this.getPaidPaywallData(paymentHash)
            ws.close()
          }
        }
      } catch (err) {
        console.warn(err)
        LNbits.utils.notifyApiError(err)
      }
    }
  },
  created() {
    const url = this.$q.localStorage.getItem(`lnbits.paywall.${paywall.id}`)
    if (url) {
      this.redirectUrl = url
    }
  }
})
