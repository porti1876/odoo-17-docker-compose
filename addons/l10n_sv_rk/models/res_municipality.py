from odoo import fields, models, api, exceptions, _


class ResMunicipality(models.Model):
    _name = "res.municipality"
    _description = "Municipios de El Salvador"

    name = fields.Char(string="Nombre", help="Nombre del municipio")
    code = fields.Char(string="Codigo", help='Code of municipality')
    dpto_id = fields.Many2one('res.country.state', _("State"), help=_("Departamentos"))
    name_code = fields.Char(string="Nombre de Formulario")
    dpto_code = fields.Char(string="Departamento de formulario")

    def copy(self, default=None):
        default = dict(default or {})

        copied_count = self.search_count(
            [('name', '=like', _(u"Copy of {}%").format(self.name))])
        if not copied_count:
            new_name = _(u"Copy of {}").format(self.name)
        else:
            new_name = _(u"Copy of {} ({})").format(self.name, copied_count)

        copied_count = self.search_count(
            [('code', '=like', _(u"Copy of {}%").format(self.code))])
        if not copied_count:
            new_code = _(u"Copy of {}").format(self.code)
        else:
            new_code = _(u"Copy of {} ({})").format(self.code, copied_count)

        default['name'] = new_name
        default['code'] = new_code
        return super(ResMunicipality, self).copy(default)

    _sql_constraints = [
        (
            'name_code_unique',
            'UNIQUE(name,code)',
            _('The name must be unique')
        )
    ]
