window.PagePaywallDisplay = {
  template: '#page-paywall-display',
  data() {
    return {
      paywall: null,
      userAmount: 0,
      paywallAmount: 0,
      paywallCurrency: 'sat',
      paywallMemo: '',
      paywallDescription: '',
      paywallFiat: null,
      paywallErrorLabel: '',
      paymentReq: null,
      redirectUrl: null,
      paymentDialog: {
        dismissMsg: null,
        checker: null,
        websocket: null
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
        this.paymentDialog.dismissMsg = null
      }
      if (this.paymentDialog.websocket) {
        this.paymentDialog.websocket.close()
        this.paymentDialog.websocket = null
      }
    },
    createInvoice(fiat = false) {
      if (this.loading) return
      this.loading = true
      if (fiat && !this.paywallFiat) {
        this.loading = false
        Quasar.Notify.create({
          type: 'negative',
          message: 'Fiat payments are not supported for this paywall.'
        })
        return
      }
      if (fiat && this.paywallCurrency == 'sat') {
        this.loading = false
        Quasar.Notify.create({
          type: 'negative',
          message: 'This paywall is set to sats, cannot create fiat invoice.'
        })
        return
      }
      LNbits.api
        .request(
          'POST',
          `/paywall/api/v1/paywalls/invoice/${this.paywall.id}`,
          'filler',
          {
            amount: this.amount,
            pay_in_fiat: fiat
          }
        )
        .then(response => {
          if (response.data) {
            const {
              payment_hash,
              bolt11,
              extra: {fiat_payment_request}
            } = response.data
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
        `/paywall/api/v1/paywalls/check_invoice/${this.paywall.id}`,
        'filler',
        {payment_hash: paymentHash}
      )
      if (data && data.paid) {
        this.cancelPayment()
        this.redirectUrl = data.url
        if (data.remembers) {
          this.$q.localStorage.set(
            `lnbits.paywall.${this.paywall.id}`,
            data.url
          )
        }
      }
    },
    subscribeToPaymentWS(paymentHash) {
      try {
        if (this.paymentDialog.websocket) {
          this.paymentDialog.websocket.close()
        }
        const url = new URL(window.location)
        url.protocol = url.protocol === 'https:' ? 'wss' : 'ws'
        url.pathname = `/api/v1/ws/${paymentHash}`
        const ws = new WebSocket(url)
        this.paymentDialog.websocket = ws
        ws.onmessage = async ({data}) => {
          const payment = JSON.parse(data)
          if (payment.pending === false) {
            Quasar.Notify.create({
              type: 'positive',
              message: 'Invoice Paid!'
            })
            this.getPaidPaywallData(paymentHash)
            ws.close()
            this.paymentDialog.websocket = null
          }
        }
      } catch (err) {
        console.warn(err)
        LNbits.utils.notifyApiError(err)
      }
    },
    async getPaywall() {
      let data
      try {
        const response = await LNbits.api.request(
          'GET',
          `/paywall/api/v1/paywalls/${this.$route.params.id}`
        )
        data = response.data
      } catch (error) {
        this.paywallErrorLabel = 'Paywall unavailable.'
        LNbits.utils.notifyApiError(error)
        return
      }
      this.paywall = data
      this.userAmount = data.amount
      this.paywallAmount = data.amount
      this.paywallCurrency = data.currency
      this.paywallMemo = data.memo
      this.paywallDescription = data.description
      this.paywallFiat = data.fiat_provider
    }
  },
  async created() {
    await this.getPaywall()
    if (!this.paywall) return
    const url = this.$q.localStorage.getItem(
      `lnbits.paywall.${this.paywall.id}`
    )
    if (url) {
      this.redirectUrl = url
    }
  }
}
