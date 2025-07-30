const mapPaywall = obj => {
  obj.date = Quasar.date.formatDate(new Date(obj.time), 'YYYY-MM-DD HH:mm')
  obj.fsat = new Intl.NumberFormat(LOCALE).format(obj.amount)
  obj.displayUrl = ['/paywall/', obj.id].join('')
  obj.downloadUrl = ['/paywall/download/', obj.id].join('')
  obj.type = obj.extras?.type
  obj.fileUrl = obj.extras?.file_config?.url
  if (obj.extras?.file_config?.headers) {
    obj.headers = Object.entries(obj.extras?.file_config?.headers).map(h => ({
      key: h[0],
      value: h[1]
    }))
  }
  return obj
}

window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data() {
    return {
      paywalls: [],
      paywallsTable: {
        columns: [
          {name: 'id', align: 'left', label: 'ID', field: 'id'},
          {name: 'memo', align: 'left', label: 'Memo', field: 'memo'},
          {
            name: 'currency',
            align: 'left',
            label: 'Currency',
            field: 'currency'
          },
          {
            name: 'amount',
            align: 'right',
            label: 'Amount',
            field: 'fsat',
            sortable: true,
            sort(a, b, rowA, rowB) {
              return rowA.amount - rowB.amount
            }
          },
          {
            name: 'fiat_provider',
            align: 'left',
            label: 'Fiat Provider',
            field: 'fiat_provider',
            format: val => val && val.charAt(0).toUpperCase() + val.slice(1)
          },
          {
            name: 'remembers',
            align: 'left',
            label: 'Remember',
            field: 'remembers'
          },
          {
            name: 'date',
            align: 'left',
            label: 'Date',
            field: 'date',
            sortable: true
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      formDialog: {
        show: false,
        showAdvanced: false,
        data: null
      },
      paywallTypeOptions: [
        {id: 'url', label: 'Redirect URL'},
        {id: 'file', label: 'File Download'}
      ],
      currencyOptions: [],
      fiatProviders: []
    }
  },
  computed: {
    extras() {
      const type = this.formDialog.data.type.id
      let file_config = null
      if (type === 'file') {
        file_config = {
          url: this.formDialog.data.fileUrl,
          headers: this.formDialog.data.headers
            .filter(v => !!v.key)
            .reduce((a, h) => {
              a[h.key] = h.value
              return a
            }, {})
        }
      }
      return {type, file_config}
    },
    isValidForm() {
      const url =
        this.formDialog.data.type.id === 'url'
          ? this.formDialog.data.url
          : this.formDialog.data.fileUrl

      return (
        url &&
        this.formDialog.data.amount &&
        this.formDialog.data.amount >= 0 &&
        this.formDialog.data.memo
      )
    }
  },
  methods: {
    emptyPaywall() {
      return {
        remembers: false,
        type: this.paywallTypeOptions[0],
        url: null,
        fileUrl: null,
        headers: []
      }
    },
    getPaywalls() {
      LNbits.api
        .request(
          'GET',
          '/paywall/api/v1/paywalls?all_wallets=true',
          this.g.user.wallets[0].inkey
        )
        .then(response => {
          this.paywalls = response.data.map(obj => {
            return mapPaywall(obj)
          })
        })
    },
    showPaywallDialog(paywallData) {
      this.formDialog.show = true
      this.formDialog.data = paywallData || this.emptyPaywall()
    },
    async createoOrUpdatePaywall() {
      try {
        const paywall = {
          url: this.formDialog.data.url || '',
          memo: this.formDialog.data.memo,
          currency: this.formDialog.data.currency,
          amount: this.formDialog.data.amount,
          fiat_provider: this.formDialog.data.fiat_provider || null,
          description: this.formDialog.data.description,
          remembers: this.formDialog.data.remembers,
          extras: this.extras
        }

        const paywallId = this.formDialog.data.id
        let method = 'POST'
        let path = '/paywall/api/v1/paywalls'
        const adminkey = _.findWhere(this.g.user.wallets, {
          id: this.formDialog.data.wallet
        }).adminkey

        if (paywallId) {
          method = 'PATCH'
          path = `/paywall/api/v1/paywalls/${paywallId}`
        }

        const {data} = await LNbits.api.request(method, path, adminkey, paywall)

        this.paywalls = this.paywalls.filter(p => p.id !== data.id)
        this.paywalls.unshift(mapPaywall(data))

        this.formDialog.show = false
        this.formDialog.data = this.emptyPaywall()
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    editPaywall(paywallId) {
      let paywall = this.paywalls.find(p => p.id === paywallId) || {}
      paywall = {...this.emptyPaywall(), ...paywall}
      paywall.type =
        this.paywallTypeOptions.find(p => paywall.type === p.id) ||
        this.paywallTypeOptions[0]
      this.showPaywallDialog(paywall)
    },
    deletePaywall(paywallId) {
      const paywall = _.findWhere(this.paywalls, {id: paywallId})
      LNbits.utils
        .confirmDialog('Are you sure you want to delete this paywall link?')
        .onOk(() => {
          LNbits.api
            .request(
              'DELETE',
              '/paywall/api/v1/paywalls/' + paywallId,
              _.findWhere(this.g.user.wallets, {id: paywall.wallet}).adminkey
            )
            .then(response => {
              this.paywalls = _.reject(this.paywalls, obj => {
                return obj.id == paywallId
              })
            })
            .catch(LNbits.utils.notifyApiError)
        })
    },
    addFileHttpHeader() {
      this.formDialog.data.headers = this.formDialog.data.headers || []
      this.formDialog.data.headers.push({key: '', value: ''})
    },
    removeFileHttpHeader(index) {
      if (index < this.formDialog.data.headers.length) {
        this.formDialog.data.headers.splice(index, 1)
      }
    },
    exportCSV() {
      LNbits.utils.exportCSV(this.paywallsTable.columns, this.paywalls)
    },
    copyToClipboard(url) {
      const {protocol, host, port} = window.location
      Quasar.copyToClipboard(`${protocol}//${host}${url}`).then(() => {
        Quasar.Notify.create({
          message: 'Copied to clipboard!',
          position: 'bottom'
        })
      })
    }
  },
  created() {
    if (this.g.user.wallets.length) {
      this.getPaywalls()
    }
    LNbits.api
      .request('GET', '/api/v1/currencies')
      .then(response => {
        this.currencyOptions = ['sat', ...response.data]
        if (LNBITS_DENOMINATION != 'sats') {
          this.formDialog.data.currency = LNBITS_DENOMINATION
        }
      })
      .catch(err => {
        LNbits.utils.notifyApiError(err)
      })
    if (this.g.user.fiat_providers && this.g.user.fiat_providers.length > 0) {
      this.fiatProviders = [...this.g.user.fiat_providers]
    }
  }
})
