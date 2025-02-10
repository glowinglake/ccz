class Hero:
    # Growth rates per hero type
    GROWTH_RATES = {
        'cav': {'hp': 6, 'mp': 2, 'attack': 3, 'defense': 2, 'spirit': 1},
        'archer': {'hp': 4, 'mp': 3, 'attack': 4, 'defense': 1, 'spirit': 2},
        'footman': {'hp': 5, 'mp': 2, 'attack': 2, 'defense': 4, 'spirit': 1},
        'king': {'hp': 7, 'mp': 4, 'attack': 3, 'defense': 3, 'spirit': 3},
    }

    def __init__(self, hero_id, hero_type, level, current_exp, hp, mp, attack, defense, spirit):
        if hero_type not in self.GROWTH_RATES:
            raise ValueError(f"Invalid hero type. Must be one of: {', '.join(self.GROWTH_RATES.keys())}")
            
        self.hero_id = hero_id
        self.hero_type = hero_type
        self.level = level
        self.current_exp = current_exp
        self.hp = hp
        self.mp = mp
        self.attack = attack
        self.defense = defense
        self.spirit = spirit
        
        # Initialize equipment slots (using integers as placeholders)
        self.weapon = None
        self.armor = None
        self.other = None

    def gain_exp(self, amount):
        self.current_exp += amount
        if self.current_exp >= 100:
            self.current_exp -= 100
            self.level_up()

    def level_up(self):
        self.level += 1
        growth = self.GROWTH_RATES[self.hero_type]
        
        # Apply type-specific stat growth
        self.hp += growth['hp']
        self.mp += growth['mp']
        self.attack += growth['attack']
        self.defense += growth['defense']
        self.spirit += growth['spirit']

    def equip_item(self, slot, item_id):
        """
        Equip an item in the specified slot
        :param slot: 'weapon', 'armor', or 'other'
        :param item_id: integer placeholder for item reference
        """
        if slot not in ['weapon', 'armor', 'other']:
            raise ValueError("Invalid equipment slot")
            
        setattr(self, slot, item_id)

