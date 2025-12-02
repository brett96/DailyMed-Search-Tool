from django.db import models


class Rxnatomarchive(models.Model):
    rxaui = models.CharField(max_length=8, blank=True, null=True)
    aui = models.CharField(max_length=10, blank=True, null=True)
    str = models.CharField(max_length=4000, blank=True, null=True)
    archive_timestamp = models.CharField(max_length=280, blank=True, null=True)
    created_timestamp = models.CharField(max_length=280, blank=True, null=True)
    updated_timestamp = models.CharField(max_length=280, blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    is_brand = models.CharField(max_length=1, blank=True, null=True)
    lat = models.CharField(max_length=3, blank=True, null=True)
    last_released = models.CharField(max_length=30, blank=True, null=True)
    saui = models.CharField(max_length=50, blank=True, null=True)
    vsab = models.CharField(max_length=40, blank=True, null=True)
    rxcui = models.CharField(max_length=8, blank=True, null=True)
    sab = models.CharField(max_length=20, blank=True, null=True)
    tty = models.CharField(max_length=20, blank=True, null=True)
    merged_to_rxcui = models.CharField(max_length=8, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rxnatomarchive'
        db_table_comment = 'Archived atom data'


class Rxnconso(models.Model):
    rxcui = models.CharField(max_length=8, blank=True, null=True)
    lat = models.CharField(max_length=3, blank=True, null=True)
    ts = models.CharField(max_length=1, blank=True, null=True)
    lui = models.CharField(max_length=8, blank=True, null=True)
    stt = models.CharField(max_length=3, blank=True, null=True)
    sui = models.CharField(max_length=8, blank=True, null=True)
    ispref = models.CharField(max_length=1, blank=True, null=True)
    rxaui = models.CharField(max_length=8, blank=True, null=True)
    saui = models.CharField(max_length=50, blank=True, null=True)
    scui = models.CharField(max_length=50, blank=True, null=True)
    sdui = models.CharField(max_length=50, blank=True, null=True)
    sab = models.CharField(max_length=20, blank=True, null=True)
    tty = models.CharField(max_length=20, blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    str = models.CharField(max_length=3000, blank=True, null=True)
    srl = models.CharField(max_length=10, blank=True, null=True)
    suppress = models.CharField(max_length=1, blank=True, null=True)
    cvf = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rxnconso'
        db_table_comment = 'Concept names and sources - main concepts table'


class Rxncui(models.Model):
    cui1 = models.CharField(max_length=8, blank=True, null=True)
    ver = models.CharField(max_length=10, blank=True, null=True)
    cardinality = models.CharField(max_length=8, blank=True, null=True)
    cui2 = models.CharField(max_length=8, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rxncui'
        db_table_comment = 'Retired concept tracking'


class Rxncuichanges(models.Model):
    rxaui = models.CharField(max_length=8, blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    sab = models.CharField(max_length=20, blank=True, null=True)
    tty = models.CharField(max_length=20, blank=True, null=True)
    str = models.CharField(max_length=3000, blank=True, null=True)
    old_rxcui = models.CharField(max_length=8, blank=True, null=True)
    new_rxcui = models.CharField(max_length=8, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rxncuichanges'
        db_table_comment = 'Concept change tracking'


class Rxndoc(models.Model):
    dockey = models.CharField(max_length=50, blank=True, null=True)
    value = models.CharField(max_length=1000, blank=True, null=True)
    type = models.CharField(max_length=50, blank=True, null=True)
    expl = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rxndoc'
        db_table_comment = 'Documentation for abbreviated values'


class Rxnrel(models.Model):
    rxcui1 = models.CharField(max_length=8, blank=True, null=True)
    rxaui1 = models.CharField(max_length=8, blank=True, null=True)
    stype1 = models.CharField(max_length=50, blank=True, null=True)
    rel = models.CharField(max_length=4, blank=True, null=True)
    rxcui2 = models.CharField(max_length=8, blank=True, null=True)
    rxaui2 = models.CharField(max_length=8, blank=True, null=True)
    stype2 = models.CharField(max_length=50, blank=True, null=True)
    rela = models.CharField(max_length=100, blank=True, null=True)
    rui = models.CharField(max_length=10, blank=True, null=True)
    srui = models.CharField(max_length=50, blank=True, null=True)
    sab = models.CharField(max_length=20, blank=True, null=True)
    sl = models.CharField(max_length=1000, blank=True, null=True)
    dir = models.CharField(max_length=1, blank=True, null=True)
    rg = models.CharField(max_length=10, blank=True, null=True)
    suppress = models.CharField(max_length=1, blank=True, null=True)
    cvf = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rxnrel'
        db_table_comment = 'Relationships between concepts'


class Rxnsab(models.Model):
    vcui = models.CharField(max_length=8, blank=True, null=True)
    rcui = models.CharField(max_length=8, blank=True, null=True)
    vsab = models.CharField(max_length=40, blank=True, null=True)
    rsab = models.CharField(max_length=20, blank=True, null=True)
    son = models.CharField(max_length=3000, blank=True, null=True)
    sf = models.CharField(max_length=20, blank=True, null=True)
    sver = models.CharField(max_length=20, blank=True, null=True)
    vstart = models.CharField(max_length=10, blank=True, null=True)
    vend = models.CharField(max_length=10, blank=True, null=True)
    imeta = models.CharField(max_length=10, blank=True, null=True)
    rmeta = models.CharField(max_length=10, blank=True, null=True)
    slc = models.CharField(max_length=1000, blank=True, null=True)
    scc = models.CharField(max_length=1000, blank=True, null=True)
    srl = models.CharField(max_length=10, blank=True, null=True)
    tfr = models.CharField(max_length=10, blank=True, null=True)
    cfr = models.CharField(max_length=10, blank=True, null=True)
    cxty = models.CharField(max_length=50, blank=True, null=True)
    ttyl = models.CharField(max_length=300, blank=True, null=True)
    atnl = models.CharField(max_length=1000, blank=True, null=True)
    lat = models.CharField(max_length=3, blank=True, null=True)
    cenc = models.CharField(max_length=20, blank=True, null=True)
    curver = models.CharField(max_length=1, blank=True, null=True)
    sabin = models.CharField(max_length=1, blank=True, null=True)
    ssn = models.CharField(max_length=3000, blank=True, null=True)
    scit = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rxnsab'
        db_table_comment = 'Source vocabulary information'


class Rxnsat(models.Model):
    rxcui = models.CharField(max_length=8, blank=True, null=True)
    lui = models.CharField(max_length=8, blank=True, null=True)
    sui = models.CharField(max_length=8, blank=True, null=True)
    rxaui = models.CharField(max_length=8, blank=True, null=True)
    stype = models.CharField(max_length=50, blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    atui = models.CharField(max_length=11, blank=True, null=True)
    satui = models.CharField(max_length=50, blank=True, null=True)
    atn = models.CharField(max_length=1000, blank=True, null=True)
    sab = models.CharField(max_length=20, blank=True, null=True)
    atv = models.TextField(blank=True, null=True)
    suppress = models.CharField(max_length=1, blank=True, null=True)
    cvf = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rxnsat'
        db_table_comment = 'Concept and atom attributes'


class Rxnsty(models.Model):
    rxcui = models.CharField(max_length=8, blank=True, null=True)
    tui = models.CharField(max_length=4, blank=True, null=True)
    stn = models.CharField(max_length=100, blank=True, null=True)
    sty = models.CharField(max_length=50, blank=True, null=True)
    atui = models.CharField(max_length=11, blank=True, null=True)
    cvf = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'rxnsty'
        db_table_comment = 'Semantic type assignments'
