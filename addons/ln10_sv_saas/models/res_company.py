# -*- coding: utf-8 -*-

from odoo import models, api, _, fields


class Company(models.Model):
    _inherit="res.company"
   
    token_digi=fields.Char(string="Token DigitalOcean")