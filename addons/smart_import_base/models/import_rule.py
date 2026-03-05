import re

from odoo import fields, models

from .mapping_profile import CANONICAL_KEY_SELECTION


class SmartImportRule(models.Model):
    _name = 'smart.import.rule'
    _description = 'Smart Import Rule'
    _order = 'priority, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    profile_id = fields.Many2one('smart.import.mapping.profile', required=True, ondelete='cascade')
    applies_to = fields.Selection([
        ('product_template', 'Product Template'),
    ], required=True, default='product_template')
    when_key = fields.Selection(CANONICAL_KEY_SELECTION, required=True)
    operator = fields.Selection([
        ('equals', 'Equals'),
        ('contains', 'Contains'),
        ('regex', 'Regex'),
    ], required=True, default='equals')
    when_value = fields.Char(required=True)
    set_purchase_ok = fields.Boolean()
    add_route_buy = fields.Boolean()
    add_route_manufacture = fields.Boolean()
    note = fields.Text()
    priority = fields.Integer(default=10)

    def predicate_matches(self, value):
        self.ensure_one()
        left = str(value or '')
        right = str(self.when_value or '')
        if self.operator == 'equals':
            return left.lower() == right.lower()
        if self.operator == 'contains':
            return right.lower() in left.lower()
        if self.operator == 'regex':
            if not right:
                return False
            try:
                return bool(re.search(right, left, flags=re.IGNORECASE))
            except re.error:
                return False
        return False
