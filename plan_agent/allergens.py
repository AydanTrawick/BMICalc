"""Conservative, boundary-aware food checks. These cannot certify allergy safety."""
import re
import unicodedata

EXCLUSION_KEYWORDS = {
    'nuts': ['nut', 'almond', 'cashew', 'walnut', 'pecan', 'pistachio', 'hazelnut',
             'macadamia', 'brazil nut', 'pine nut', 'peanut', 'nut butter', 'pesto',
             'praline', 'marzipan', 'nougat', 'gianduja', 'frangipane',
             'almond milk', 'almond flour', 'groundnut'],
    'dairy': ['milk', 'cheese', 'butter', 'yogurt', 'yoghurt', 'cream', 'whey', 'casein', 'ghee'],
    'gluten': ['wheat', 'flour', 'bread', 'pasta', 'barley', 'rye', 'couscous', 'seitan'],
    'shellfish': ['shrimp', 'crab', 'lobster', 'prawn', 'scallop', 'clam', 'mussel', 'oyster'],
    'eggs': ['egg', 'mayonnaise', 'meringue'],
    'soy': ['soy', 'soya', 'tofu', 'tempeh', 'edamame', 'miso'],
}
ALIASES = {'nut': 'nuts', 'tree nuts': 'nuts', 'tree nut': 'nuts', 'egg': 'eggs',
           'dairy products': 'dairy', 'soya': 'soy'}


def normalize(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    return re.sub(r'\s+', ' ', text.replace('-', ' ').replace('–', ' ').replace('‑', ' ')).strip()


def contains_keyword(text, keyword):
    keyword = normalize(keyword)
    # "nuts" does not match coconut or nutmeg; ordinary plurals still match.
    stem = keyword[:-1] if keyword.endswith('s') and not keyword.endswith('ss') else keyword
    return bool(stem and re.search(r'(?<!\w)' + re.escape(stem) + r'(?:s|es)?(?!\w)', normalize(text)))


def exclusion_matches(text, exclusion):
    exclusion = normalize(exclusion)
    exclusion = ALIASES.get(exclusion, exclusion)
    keywords = EXCLUSION_KEYWORDS.get(exclusion, [exclusion])
    # Coconut/nutmeg only avoid a *nut* match. Coconut milk still matches dairy's
    # conservative "milk" rule. Explicit coconut/nutmeg exclusions still apply.
    return [word for word in keywords if contains_keyword(text, word)]
