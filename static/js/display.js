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
      paywallFiat: paywall.fiat_provider,
      paymentReq: null,
      redirectUrl: null,
      paymentDialog: {
        dismissMsg: null,
        checker: null
      },
      loading: false
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
    createInvoice(fiat = false) {
      if (this.loading) return
      this.loading = true
      if (fiat && !this.paywallFiat) {
        Quasar.Notify.create({
          type: 'negative',
          message: 'Fiat payments are not supported for this paywall.'
        })
        return
      }
      if (fiat && this.paywallCurrency == 'sat') {
        Quasar.Notify.create({
          type: 'negative',
          message: 'This paywall is set to sats, cannot create fiat invoice.'
        })
        return
      }
      LNbits.api
        .request(
          'POST',
          `/paywall/api/v1/paywalls/invoice/${paywall.id}`,
          'filler',
          {
            amount: this.amount,
            pay_in_fiat: fiat,
          }
        )
        .then(response => {
          if (response.data) {
            const { payment_hash, bolt11, extra: { fiat_payment_request } } = response.data
            if (fiat && fiat_payment_request) {
              this.paymentReq = fiat_payment_request
            } else {
              this.paymentReq = `lightning:${bolt11.toUpperCase()}`
            }
            this.paymentDialog.dismissMsg = Quasar.Notify.create({
              timeout: 0,
              message: 'Waiting for payment...'
            })
            this.subscribeToPaymentWS(payment_hash)
          }
        })
        .catch(LNbits.utils.notifyApiError)
        .finally(() => {
          this.loading = false
        })
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
