<?xml version="1.0" encoding="UTF-8"?>
<!-- Referential and contextual constraints for the DoCTA accounting pilot. -->
<schema xmlns="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt">
  <title>DoCTA accounting pilot constraints</title>
  <ns prefix="tei" uri="http://www.tei-c.org/ns/1.0"/>
  <ns prefix="xml" uri="http://www.w3.org/XML/1998/namespace"/>

  <pattern id="unique-identifiers">
    <rule context="tei:*[@xml:id]">
      <assert test="count(//*[@xml:id = current()/@xml:id]) = 1">
        Every xml:id must be unique in the TEI document.
      </assert>
    </rule>
  </pattern>
  <pattern id="local-references">
    <rule context="tei:*[@ref]">
      <assert test="starts-with(@ref, '#') and //*[@xml:id = substring-after(current()/@ref, '#')]">
        Every local ref must resolve to an xml:id in the TEI document.
      </assert>
    </rule>
  </pattern>
  <pattern id="unit-references">
    <rule context="tei:*[@unitRef]">
      <assert test="starts-with(@unitRef, '#') and //tei:unitDef[@xml:id = substring-after(current()/@unitRef, '#')]">
        Every unitRef must resolve to a unitDef in the TEI header.
      </assert>
    </rule>
  </pattern>
  <pattern id="page-facsimile-references">
    <rule context="tei:pb[@facs]">
      <assert test="starts-with(@facs, '#') and //tei:surface[@xml:id = substring-after(current()/@facs, '#')]">
        A page facs reference must resolve to a surface.
      </assert>
    </rule>
  </pattern>
  <pattern id="line-facsimile-references">
    <rule context="tei:lb[@facs]">
      <assert test="starts-with(@facs, '#') and //tei:zone[@xml:id = substring-after(current()/@facs, '#')]">
        A line facs reference must resolve to a zone.
      </assert>
    </rule>
  </pattern>
  <pattern id="accounting-source-references">
    <rule context="tei:seg[@ana = 'bk:Entry' or @ana = 'bk:Transaction' or @ana = 'bk:Transfer']">
      <assert test="starts-with(@corresp, '#') and //tei:lb[@xml:id = substring-after(current()/@corresp, '#')]">
        Every accounting segment must point to its source line.
      </assert>
    </rule>
  </pattern>

  <pattern id="accounting-context">
    <rule context="tei:seg[@ana = 'bk:Entry']">
      <assert test="not(ancestor::tei:seg[@ana = 'bk:Entry' or @ana = 'bk:Transaction' or @ana = 'bk:Transfer'])">
        An Entry must be the outer accounting segment.
      </assert>
      <assert test="tei:seg[@ana = 'bk:Transaction']">
        Every Entry must contain at least one Transaction.
      </assert>
    </rule>
    <rule context="tei:seg[@ana = 'bk:Transaction']">
      <assert test="parent::tei:seg[@ana = 'bk:Entry']">
        A Transaction must be a direct child of an Entry.
      </assert>
      <assert test="tei:seg[@ana = 'bk:Transfer']">
        Every Transaction must contain at least one Transfer.
      </assert>
    </rule>
    <rule context="tei:seg[@ana = 'bk:Transfer']">
      <assert test="parent::tei:seg[@ana = 'bk:Transaction']">
        A Transfer must be a direct child of a Transaction.
      </assert>
      <assert test=".//tei:measure or .//tei:measureGrp">
        Every Transfer must contain a resource expressed as measure or measureGrp.
      </assert>
    </rule>
    <rule context="tei:measure | tei:measureGrp">
      <assert test="ancestor::tei:seg[@ana = 'bk:Transfer']">
        Measures must occur inside a Transfer.
      </assert>
    </rule>
  </pattern>

  <pattern id="person-register-references">
    <rule context="tei:persName[@ref][ancestor::tei:text]">
      <assert test="//tei:listPerson/tei:person[@xml:id = substring-after(current()/@ref, '#')]">
        An inline persName must resolve to a person in listPerson.
      </assert>
    </rule>
  </pattern>
  <pattern id="organisation-register-references">
    <rule context="tei:orgName[@ref][ancestor::tei:text]">
      <assert test="//tei:listOrg/tei:org[@xml:id = substring-after(current()/@ref, '#')]">
        An inline orgName must resolve to an org in listOrg.
      </assert>
    </rule>
  </pattern>
  <pattern id="place-register-references">
    <rule context="tei:placeName[@ref][ancestor::tei:text]">
      <assert test="//tei:listPlace/tei:place[@xml:id = substring-after(current()/@ref, '#')]">
        An inline placeName must resolve to a place in listPlace.
      </assert>
    </rule>
  </pattern>
  <pattern id="source-rubric-references">
    <rule context="tei:seg[@ana = 'bk:Entry'][@type]">
      <assert test="//tei:taxonomy[@xml:id = 'tax-source-rubrics']//tei:category[@xml:id = current()/@type]">
        Entry type must resolve in the source-rubrics taxonomy.
      </assert>
    </rule>
  </pattern>
  <pattern id="account-category-references">
    <rule context="tei:seg[@ana = 'bk:Entry'][@subtype]">
      <assert test="//tei:taxonomy[@xml:id = 'tax-account-categories']//tei:category[@xml:id = current()/@subtype]">
        Entry subtype must resolve in the account-categories taxonomy.
      </assert>
    </rule>
  </pattern>
  <pattern id="goods-category-references">
    <rule context="tei:measure[@commodity]">
      <assert test="//tei:taxonomy[@xml:id = 'tax-goods']//tei:category[@xml:id = current()/@commodity]">
        A measure commodity must resolve in the goods taxonomy.
      </assert>
    </rule>
    <rule context="tei:measure[@ana = 'bk:EconomicGood']">
      <assert test="@commodity">
        An EconomicGood measure must name a goods-taxonomy category.
      </assert>
    </rule>
  </pattern>
</schema>
