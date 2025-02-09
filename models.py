class Hero:
    def __init__(self, hero_id, hero_type, level, current_exp, hp, mp, attack, defense, spirit):
        self.hero_id = hero_id
        self.hero_type = hero_type
        self.level = level
        self.current_exp = current_exp
        self.hp = hp
        self.mp = mp
        self.attack = attack
        self.defense = defense
        self.spirit = spirit

    def gain_exp(self, amount):
        self.current_exp += amount
        if self.current_exp >= 100:
            self.current_exp -= 100
            self.level_up()

    def level_up(self):
        self.level += 1
        # Simple example of stat growth:
        self.hp += 5
        self.attack += 2
        # etc.

