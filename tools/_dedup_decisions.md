# Dedup decisions (dry-run, refined rule)

Refined rule: era priority (blogger > recent-drupal > static) wins
ONLY IF the era candidate's prose is >= 80% of the cluster max.
Otherwise: pick the prose-richest member, era-then-imgs-then-archivedAt tiebreaks.

- Total clusters: 41
- Total files demoted: 54
- Choices changed vs. original era-priority rule: 13
- Risky / manual-review clusters: 16

---

## Clusters where the refined rule CHANGED the choice

### [articles] forcing rhubarb RISKY

- **Canonical:** `forcing-rhubarb-4.md` — mode=prose-richest; era=static; prose=4526 (100% of max 4526)
  - era=static, archivedAt=2008-10-18T23:50:19Z, local_imgs=1, ext_imgs=0, prose=4526
- **Original-rule pick (overridden):** `forcing-rhubarb.md` — era=blogger, archivedAt=2024-10-14T02:06:15Z, local_imgs=2, ext_imgs=0, prose=2821
- **Demoted:**
  - `forcing-rhubarb.md` — era=blogger, archivedAt=2024-10-14T02:06:15Z, local_imgs=2, ext_imgs=0, prose=2821
  - `forcing-rhubarb-2.md` — era=drupal, archivedAt=2020-03-02T05:52:34Z, local_imgs=4, ext_imgs=0, prose=3336
  - `forcing-rhubarb-3.md` — era=drupal, archivedAt=2019-06-30T16:31:15Z, local_imgs=4, ext_imgs=0, prose=3336
- **Flags:**
  - rule-change: refined rule picks forcing-rhubarb-4.md; original era-priority would pick forcing-rhubarb.md
  - loser forcing-rhubarb.md has 2 local imgs vs canonical 1
  - loser forcing-rhubarb-2.md has 4 local imgs vs canonical 1
  - loser forcing-rhubarb-3.md has 4 local imgs vs canonical 1

### [articles] medicinal uses of rhubarb RISKY

- **Canonical:** `medicinal-uses-of-rhubarb-2.md` — mode=prose-richest; era=static; prose=9573 (100% of max 9573)
  - era=static, archivedAt=2008-10-17T08:50:07Z, local_imgs=2, ext_imgs=0, prose=9573
- **Original-rule pick (overridden):** `medicinal-uses-of-rhubarb.md` — era=drupal, archivedAt=2020-03-02T05:52:54Z, local_imgs=2, ext_imgs=0, prose=4176
- **Demoted:**
  - `medicinal-uses-of-rhubarb.md` — era=drupal, archivedAt=2020-03-02T05:52:54Z, local_imgs=2, ext_imgs=0, prose=4176
- **Flags:**
  - rule-change: refined rule picks medicinal-uses-of-rhubarb-2.md; original era-priority would pick medicinal-uses-of-rhubarb.md

### [articles] rhubarb festivals RISKY

- **Canonical:** `rhubarb-festivals-2.md` — mode=prose-richest; era=static; prose=2511 (100% of max 2511)
  - era=static, archivedAt=2008-10-14T06:32:15Z, local_imgs=1, ext_imgs=0, prose=2511
- **Original-rule pick (overridden):** `rhubarb-festivals.md` — era=drupal, archivedAt=2020-03-02T05:52:29Z, local_imgs=0, ext_imgs=0, prose=1768
- **Demoted:**
  - `rhubarb-festivals.md` — era=drupal, archivedAt=2020-03-02T05:52:29Z, local_imgs=0, ext_imgs=0, prose=1768
- **Flags:**
  - rule-change: refined rule picks rhubarb-festivals-2.md; original era-priority would pick rhubarb-festivals.md

### [articles] rhubarb history RISKY

- **Canonical:** `rhubarb-history-3.md` — mode=prose-richest; era=static; prose=8499 (100% of max 8499)
  - era=static, archivedAt=2008-10-17T08:49:51Z, local_imgs=1, ext_imgs=0, prose=8499
- **Original-rule pick (overridden):** `rhubarb-history.md` — era=drupal, archivedAt=2020-03-02T05:52:44Z, local_imgs=0, ext_imgs=0, prose=6715
- **Demoted:**
  - `rhubarb-history.md` — era=drupal, archivedAt=2020-03-02T05:52:44Z, local_imgs=0, ext_imgs=0, prose=6715
  - `rhubarb-history-2.md` — era=drupal, archivedAt=2019-09-01T12:17:41Z, local_imgs=0, ext_imgs=0, prose=6715
- **Flags:**
  - rule-change: refined rule picks rhubarb-history-3.md; original era-priority would pick rhubarb-history.md

### [articles] rhubarb recipes RISKY

- **Canonical:** `rhubarb-recipes-2.md` — mode=prose-richest; era=static; prose=3213 (100% of max 3213)
  - era=static, archivedAt=2008-11-08T13:02:41Z, local_imgs=1, ext_imgs=0, prose=3213
- **Original-rule pick (overridden):** `rhubarb-recipes-3.md` — era=drupal, archivedAt=2020-03-02T05:53:29Z, local_imgs=0, ext_imgs=1, prose=2226
- **Demoted:**
  - `rhubarb-recipes-3.md` — era=drupal, archivedAt=2020-03-02T05:53:29Z, local_imgs=0, ext_imgs=1, prose=2226
  - `rhubarb-recipes.md` — era=drupal, archivedAt=2020-02-24T15:16:23Z, local_imgs=0, ext_imgs=1, prose=2226
- **Flags:**
  - rule-change: refined rule picks rhubarb-recipes-2.md; original era-priority would pick rhubarb-recipes-3.md

### [articles] rhubarb seedpods RISKY

- **Canonical:** `rhubarb-seedpods-2.md` — mode=prose-richest; era=drupal; archivedAt=2019-08-21T17:25:06Z; prose=1975 (100% of max 1975)
  - era=drupal, archivedAt=2019-08-21T17:25:06Z, local_imgs=6, ext_imgs=0, prose=1975
- **Original-rule pick (overridden):** `rhubarb-seedpods.md` — era=blogger, archivedAt=2024-09-20T21:08:57Z, local_imgs=3, ext_imgs=0, prose=1568
- **Demoted:**
  - `rhubarb-seedpods.md` — era=blogger, archivedAt=2024-09-20T21:08:57Z, local_imgs=3, ext_imgs=0, prose=1568
- **Flags:**
  - rule-change: refined rule picks rhubarb-seedpods-2.md; original era-priority would pick rhubarb-seedpods.md

### [articles] rhubarb sources RISKY

- **Canonical:** `rhubarb-sources-2.md` — mode=prose-richest; era=static; prose=3191 (100% of max 3191)
  - era=static, archivedAt=2008-10-21T02:28:23Z, local_imgs=1, ext_imgs=0, prose=3191
- **Original-rule pick (overridden):** `rhubarb-sources.md` — era=drupal, archivedAt=2019-03-23T00:01:31Z, local_imgs=1, ext_imgs=0, prose=1647
- **Demoted:**
  - `rhubarb-sources.md` — era=drupal, archivedAt=2019-03-23T00:01:31Z, local_imgs=1, ext_imgs=0, prose=1647
- **Flags:**
  - rule-change: refined rule picks rhubarb-sources-2.md; original era-priority would pick rhubarb-sources.md

### [articles] rhubarb varieties RISKY

- **Canonical:** `rhubarb-varieties-4.md` — mode=prose-richest; era=static; prose=9030 (100% of max 9030); local_imgs=2, ext_imgs=0
  - era=static, archivedAt=2008-10-15T04:24:06Z, local_imgs=2, ext_imgs=0, prose=9030
- **Original-rule pick (overridden):** `rhubarb-varieties.md` — era=blogger, archivedAt=2024-09-20T20:57:50Z, local_imgs=1, ext_imgs=0, prose=5843
- **Demoted:**
  - `rhubarb-varieties.md` — era=blogger, archivedAt=2024-09-20T20:57:50Z, local_imgs=1, ext_imgs=0, prose=5843
  - `rhubarb-varieties-3.md` — era=drupal, archivedAt=2020-02-23T21:23:02Z, local_imgs=2, ext_imgs=0, prose=8166
  - `rhubarb-varieties-2.md` — era=static, archivedAt=2012-11-01T05:26:26Z, local_imgs=2, ext_imgs=0, prose=8220
- **Flags:**
  - rule-change: refined rule picks rhubarb-varieties-4.md; original era-priority would pick rhubarb-varieties.md
  - close-call: loser rhubarb-varieties-3.md prose=8166 local=2 ~= canonical prose=9030 local=2 (different eras)

### [articles] things that are not rhubarb RISKY

- **Canonical:** `things-that-are-not-rhubarb-2.md` — mode=prose-richest; era=drupal; archivedAt=2020-02-23T19:03:24Z; prose=5459 (100% of max 5459)
  - era=drupal, archivedAt=2020-02-23T19:03:24Z, local_imgs=4, ext_imgs=0, prose=5459
- **Original-rule pick (overridden):** `things-that-are-not-rhubarb.md` — era=blogger, archivedAt=2024-08-07T17:50:03Z, local_imgs=2, ext_imgs=0, prose=3992
- **Demoted:**
  - `things-that-are-not-rhubarb.md` — era=blogger, archivedAt=2024-08-07T17:50:03Z, local_imgs=2, ext_imgs=0, prose=3992
- **Flags:**
  - rule-change: refined rule picks things-that-are-not-rhubarb-2.md; original era-priority would pick things-that-are-not-rhubarb.md

### [recipes] culinary uses of rhubarb RISKY

- **Canonical:** `culinary-uses-of-rhubarb-2.md` — mode=prose-richest; era=drupal; archivedAt=2020-03-02T05:52:24Z; prose=8639 (100% of max 8639)
  - era=drupal, archivedAt=2020-03-02T05:52:24Z, local_imgs=2, ext_imgs=1, prose=8639
- **Original-rule pick (overridden):** `culinary-uses-of-rhubarb.md` — era=blogger, archivedAt=2024-09-20T21:06:55Z, local_imgs=1, ext_imgs=0, prose=6818
- **Demoted:**
  - `culinary-uses-of-rhubarb.md` — era=blogger, archivedAt=2024-09-20T21:06:55Z, local_imgs=1, ext_imgs=0, prose=6818
- **Flags:**
  - rule-change: refined rule picks culinary-uses-of-rhubarb-2.md; original era-priority would pick culinary-uses-of-rhubarb.md

### [recipes] growing rhubarb RISKY

- **Canonical:** `growing-rhubarb-4.md` — mode=prose-richest; era=static; prose=15332 (100% of max 15332)
  - era=static, archivedAt=2008-10-14T07:56:34Z, local_imgs=1, ext_imgs=0, prose=15332
- **Original-rule pick (overridden):** `growing-rhubarb.md` — era=blogger, archivedAt=2024-09-20T20:27:18Z, local_imgs=2, ext_imgs=0, prose=8507
- **Demoted:**
  - `growing-rhubarb.md` — era=blogger, archivedAt=2024-09-20T20:27:18Z, local_imgs=2, ext_imgs=0, prose=8507
  - `growing-rhubarb-2.md` — era=drupal, archivedAt=2020-01-28T13:28:07Z, local_imgs=2, ext_imgs=0, prose=10161
  - `growing-rhubarb-3.md` — era=drupal, archivedAt=2019-12-31T02:32:21Z, local_imgs=2, ext_imgs=0, prose=10161
- **Flags:**
  - rule-change: refined rule picks growing-rhubarb-4.md; original era-priority would pick growing-rhubarb.md
  - loser growing-rhubarb.md has 2 local imgs vs canonical 1
  - loser growing-rhubarb-2.md has 2 local imgs vs canonical 1
  - loser growing-rhubarb-3.md has 2 local imgs vs canonical 1

### [recipes] rhubarb bread recipes RISKY

- **Canonical:** `rhubarb-bread-recipes-3.md` — mode=prose-richest; era=static; prose=6858 (100% of max 6858); local_imgs=0, ext_imgs=0
  - era=static, archivedAt=2001-06-20T10:42:25Z, local_imgs=0, ext_imgs=0, prose=6858
- **Original-rule pick (overridden):** `rhubarb-bread-recipes.md` — era=blogger, archivedAt=2024-09-20T19:54:52Z, local_imgs=1, ext_imgs=0, prose=5368
- **Demoted:**
  - `rhubarb-bread-recipes.md` — era=blogger, archivedAt=2024-09-20T19:54:52Z, local_imgs=1, ext_imgs=0, prose=5368
  - `rhubarb-bread-recipes-2.md` — era=static, archivedAt=2008-10-16T04:31:06Z, local_imgs=0, ext_imgs=0, prose=5783
- **Flags:**
  - rule-change: refined rule picks rhubarb-bread-recipes-3.md; original era-priority would pick rhubarb-bread-recipes.md
  - loser rhubarb-bread-recipes.md has 1 local imgs vs canonical 0

### [recipes] rhubarb soup recipes RISKY

- **Canonical:** `rhubarb-soup-recipes-2.md` — mode=prose-richest; era=static; prose=1623 (100% of max 1623)
  - era=static, archivedAt=2008-10-17T22:51:46Z, local_imgs=0, ext_imgs=0, prose=1623
- **Original-rule pick (overridden):** `rhubarb-soup-recipes.md` — era=blogger, archivedAt=2024-09-20T21:09:40Z, local_imgs=1, ext_imgs=0, prose=1283
- **Demoted:**
  - `rhubarb-soup-recipes.md` — era=blogger, archivedAt=2024-09-20T21:09:40Z, local_imgs=1, ext_imgs=0, prose=1283
- **Flags:**
  - rule-change: refined rule picks rhubarb-soup-recipes-2.md; original era-priority would pick rhubarb-soup-recipes.md
  - loser rhubarb-soup-recipes.md has 1 local imgs vs canonical 0

---

## Still RISKY (choice unchanged but flagged for review)

### [articles] other uses for rhubarb RISKY

- **Canonical:** `other-uses-for-rhubarb.md` — mode=era-candidate; era=drupal; archivedAt=2019-06-30T18:33:38Z; prose=6875 (87% of max 7867)
  - era=drupal, archivedAt=2019-06-30T18:33:38Z, local_imgs=4, ext_imgs=0, prose=6875
- **Demoted:**
  - `other-uses-for-rhubarb-2.md` — era=static, archivedAt=2008-10-21T03:29:15Z, local_imgs=5, ext_imgs=0, prose=7867
- **Flags:**
  - loser other-uses-for-rhubarb-2.md has 5 local imgs vs canonical 4

### [articles] propagating rhubarb RISKY

- **Canonical:** `propagating-rhubarb.md` — mode=era-candidate; era=blogger; prose=5499 (90% of max 6102)
  - era=blogger, archivedAt=2024-09-20T19:36:40Z, local_imgs=3, ext_imgs=0, prose=5499
- **Demoted:**
  - `propagating-rhubarb-2.md` — era=drupal, archivedAt=2020-02-23T00:07:51Z, local_imgs=6, ext_imgs=0, prose=6102
- **Flags:**
  - loser propagating-rhubarb-2.md has 6 local imgs vs canonical 3

### [recipes] rhubarb bars RISKY

- **Canonical:** `rhubarb-bars-4.md` — mode=era-candidate; era=drupal; archivedAt=2020-02-24T19:12:55Z; prose=9692 (99% of max 9741); local_imgs=2, ext_imgs=0
  - era=drupal, archivedAt=2020-02-24T19:12:55Z, local_imgs=2, ext_imgs=0, prose=9692
- **Demoted:**
  - `rhubarb-bars.md` — era=drupal, archivedAt=2014-10-09T02:47:33Z, local_imgs=2, ext_imgs=0, prose=9728
  - `rhubarb-bars-2.md` — era=drupal, archivedAt=2010-06-30T13:19:18Z, local_imgs=2, ext_imgs=0, prose=9728
  - `rhubarb-bars-3.md` — era=static, archivedAt=2013-05-18T21:20:36Z, local_imgs=2, ext_imgs=0, prose=9741
- **Flags:**
  - close-call: loser rhubarb-bars-3.md prose=9741 local=2 ~= canonical prose=9692 local=2 (different eras)

---

## Clean clusters (no flags)

### [articles] about

- **Canonical:** `about.md` — mode=era-candidate; era=drupal; archivedAt=2020-03-02T05:52:08Z; prose=2579 (100% of max 2579); local_imgs=1, ext_imgs=1
  - era=drupal, archivedAt=2020-03-02T05:52:08Z, local_imgs=1, ext_imgs=1, prose=2579
- **Demoted:**
  - `about-2.md` — era=drupal, archivedAt=2020-01-20T07:52:02Z, local_imgs=1, ext_imgs=1, prose=2579

### [articles] composting rhubarb

- **Canonical:** `composting-rhubarb.md` — mode=era-candidate; era=drupal; archivedAt=2020-03-02T05:52:18Z; prose=1390 (100% of max 1390); local_imgs=2, ext_imgs=0
  - era=drupal, archivedAt=2020-03-02T05:52:18Z, local_imgs=2, ext_imgs=0, prose=1390
- **Demoted:**
  - `composting-rhubarb-2.md` — era=drupal, archivedAt=2017-06-29T12:57:15Z, local_imgs=2, ext_imgs=0, prose=1390

### [articles] emerging rhubarb flower

- **Canonical:** `emerging-rhubarb-flower.md` — mode=era-candidate; era=drupal; archivedAt=2020-02-01T02:20:35Z; prose=72 (100% of max 72); local_imgs=0, ext_imgs=1
  - era=drupal, archivedAt=2020-02-01T02:20:35Z, local_imgs=0, ext_imgs=1, prose=72
- **Demoted:**
  - `emerging-rhubarb-flower-2.md` — era=drupal, archivedAt=2016-08-27T10:09:21Z, local_imgs=0, ext_imgs=1, prose=72

### [articles] growing rhubarb from seed

- **Canonical:** `growing-rhubarb-from-seed-2.md` — mode=era-candidate; era=drupal; archivedAt=2020-03-02T05:52:59Z; prose=3342 (100% of max 3342); local_imgs=2, ext_imgs=0
  - era=drupal, archivedAt=2020-03-02T05:52:59Z, local_imgs=2, ext_imgs=0, prose=3342
- **Demoted:**
  - `growing-rhubarb-from-seed.md` — era=drupal, archivedAt=2020-03-02T04:27:57Z, local_imgs=2, ext_imgs=0, prose=3342

### [articles] nutritional information

- **Canonical:** `nutritional-information-2.md` — mode=era-candidate; era=drupal; archivedAt=2019-12-28T17:07:58Z; prose=816 (100% of max 816); local_imgs=2, ext_imgs=0
  - era=drupal, archivedAt=2019-12-28T17:07:58Z, local_imgs=2, ext_imgs=0, prose=816
- **Demoted:**
  - `nutritional-information.md` — era=drupal, archivedAt=2019-07-01T00:01:06Z, local_imgs=2, ext_imgs=0, prose=816

### [articles] poison information

- **Canonical:** `poison-information-2.md` — mode=era-candidate; era=drupal; archivedAt=2020-02-26T22:11:59Z; prose=6410 (100% of max 6410); local_imgs=1, ext_imgs=4
  - era=drupal, archivedAt=2020-02-26T22:11:59Z, local_imgs=1, ext_imgs=4, prose=6410
- **Demoted:**
  - `poison-information.md` — era=drupal, archivedAt=2020-02-23T00:10:27Z, local_imgs=1, ext_imgs=4, prose=6410

### [articles] rhubarb botanical information

- **Canonical:** `rhubarb-botanical-information.md` — mode=era-candidate; era=drupal; archivedAt=2020-03-02T05:52:13Z; prose=3466 (100% of max 3466); local_imgs=3, ext_imgs=0
  - era=drupal, archivedAt=2020-03-02T05:52:13Z, local_imgs=3, ext_imgs=0, prose=3466
- **Demoted:**
  - `rhubarb-botanical-information-2.md` — era=drupal, archivedAt=2020-02-01T02:14:55Z, local_imgs=3, ext_imgs=0, prose=3466

### [articles] rhubarb species

- **Canonical:** `rhubarb-species.md` — mode=era-candidate; era=blogger; prose=4378 (89% of max 4923)
  - era=blogger, archivedAt=2024-10-14T02:06:43Z, local_imgs=2, ext_imgs=0, prose=4378
- **Demoted:**
  - `rhubarb-species-2.md` — era=drupal, archivedAt=2019-06-29T23:10:14Z, local_imgs=2, ext_imgs=0, prose=4923

### [articles] table of contents

- **Canonical:** `table-of-contents.md` — mode=era-candidate; era=drupal; archivedAt=2020-03-02T05:45:02Z; prose=768 (100% of max 768); local_imgs=1, ext_imgs=0
  - era=drupal, archivedAt=2020-03-02T05:45:02Z, local_imgs=1, ext_imgs=0, prose=768
- **Demoted:**
  - `table-of-contents-2.md` — era=drupal, archivedAt=2019-05-12T05:04:36Z, local_imgs=1, ext_imgs=0, prose=768

### [pages] welcome

- **Canonical:** `welcome.md` — mode=era-candidate; era=drupal; archivedAt=2020-03-20T23:07:26Z; prose=1705 (100% of max 1705); local_imgs=2, ext_imgs=1
  - era=drupal, archivedAt=2020-03-20T23:07:26Z, local_imgs=2, ext_imgs=1, prose=1705
- **Demoted:**
  - `welcome-2.md` — era=drupal, archivedAt=2019-05-11T02:06:59Z, local_imgs=2, ext_imgs=1, prose=1705

### [recipes] frozen rhubarb recipes

- **Canonical:** `frozen-rhubarb-recipes.md` — mode=era-candidate; era=blogger; prose=5859 (93% of max 6331)
  - era=blogger, archivedAt=2024-10-14T02:50:42Z, local_imgs=1, ext_imgs=0, prose=5859
- **Demoted:**
  - `frozen-rhubarb-recipes-2.md` — era=static, archivedAt=2008-10-17T22:51:42Z, local_imgs=0, ext_imgs=0, prose=6331

### [recipes] rhubarb bar recipes

- **Canonical:** `rhubarb-bar-recipes.md` — mode=era-candidate; era=blogger; prose=9679 (94% of max 10289)
  - era=blogger, archivedAt=2024-06-22T00:33:28Z, local_imgs=1, ext_imgs=0, prose=9679
- **Demoted:**
  - `rhubarb-bar-recipes-2.md` — era=static, archivedAt=2008-10-14T07:56:18Z, local_imgs=0, ext_imgs=0, prose=10289

### [recipes] rhubarb cake recipes

- **Canonical:** `rhubarb-cake-recipes.md` — mode=era-candidate; era=static; prose=41131 (97% of max 42329); local_imgs=0, ext_imgs=0
  - era=static, archivedAt=2008-11-06T13:46:20Z, local_imgs=0, ext_imgs=0, prose=41131
- **Demoted:**
  - `rhubarb-cake-recipes-2.md` — era=static, archivedAt=2001-07-21T13:45:13Z, local_imgs=0, ext_imgs=0, prose=42329

### [recipes] rhubarb cobbler recipes

- **Canonical:** `rhubarb-cobbler-recipes.md` — mode=era-candidate; era=blogger; prose=34930 (96% of max 36538)
  - era=blogger, archivedAt=2024-10-14T01:57:45Z, local_imgs=1, ext_imgs=0, prose=34930
- **Demoted:**
  - `rhubarb-cobbler-recipes-2.md` — era=static, archivedAt=2008-10-15T04:23:31Z, local_imgs=0, ext_imgs=0, prose=36538

### [recipes] rhubarb cookie recipes

- **Canonical:** `rhubarb-cookie-recipes.md` — mode=era-candidate; era=blogger; prose=2240 (90% of max 2478)
  - era=blogger, archivedAt=2024-09-20T21:11:02Z, local_imgs=1, ext_imgs=0, prose=2240
- **Demoted:**
  - `rhubarb-cookie-recipes-2.md` — era=static, archivedAt=2008-10-15T04:23:36Z, local_imgs=0, ext_imgs=0, prose=2478

### [recipes] rhubarb dessert recipes

- **Canonical:** `rhubarb-dessert-recipes.md` — mode=era-candidate; era=blogger; prose=8732 (95% of max 9211)
  - era=blogger, archivedAt=2024-09-20T19:51:01Z, local_imgs=1, ext_imgs=0, prose=8732
- **Demoted:**
  - `rhubarb-dessert-recipes-2.md` — era=static, archivedAt=2008-10-15T04:23:41Z, local_imgs=0, ext_imgs=0, prose=9211

### [recipes] rhubarb jam recipes

- **Canonical:** `rhubarb-jam-recipes.md` — mode=era-candidate; era=blogger; prose=25917 (93% of max 27832)
  - era=blogger, archivedAt=2024-10-14T02:55:45Z, local_imgs=1, ext_imgs=0, prose=25917
- **Demoted:**
  - `rhubarb-jam-recipes-2.md` — era=static, archivedAt=2008-10-14T07:56:23Z, local_imgs=0, ext_imgs=0, prose=27202
  - `rhubarb-jam-recipes-3.md` — era=static, archivedAt=2001-01-24T10:50:00Z, local_imgs=0, ext_imgs=0, prose=27832

### [recipes] rhubarb muffin recipes

- **Canonical:** `rhubarb-muffin-recipes.md` — mode=era-candidate; era=blogger; prose=10715 (95% of max 11310)
  - era=blogger, archivedAt=2024-08-07T18:30:15Z, local_imgs=1, ext_imgs=0, prose=10715
- **Demoted:**
  - `rhubarb-muffin-recipes-2.md` — era=static, archivedAt=2008-10-16T04:31:16Z, local_imgs=0, ext_imgs=0, prose=11310

### [recipes] rhubarb muffins

- **Canonical:** `rhubarb-muffins.md` — mode=era-candidate; era=drupal; archivedAt=2020-02-23T22:01:10Z; prose=10728 (100% of max 10728); local_imgs=2, ext_imgs=0
  - era=drupal, archivedAt=2020-02-23T22:01:10Z, local_imgs=2, ext_imgs=0, prose=10728
- **Demoted:**
  - `rhubarb-muffins-2.md` — era=drupal, archivedAt=2010-06-30T13:35:05Z, local_imgs=2, ext_imgs=0, prose=10728

### [recipes] rhubarb pie recipes

- **Canonical:** `rhubarb-pie-recipes.md` — mode=era-candidate; era=blogger; prose=50357 (96% of max 52711)
  - era=blogger, archivedAt=2024-10-14T01:10:22Z, local_imgs=1, ext_imgs=0, prose=50357
- **Demoted:**
  - `rhubarb-pie-recipes-2.md` — era=static, archivedAt=2008-11-07T22:16:26Z, local_imgs=0, ext_imgs=0, prose=51897
  - `rhubarb-pie-recipes-3.md` — era=static, archivedAt=2001-06-24T07:16:43Z, local_imgs=0, ext_imgs=0, prose=52711

### [recipes] rhubarb pudding recipes

- **Canonical:** `rhubarb-pudding-recipes.md` — mode=era-candidate; era=blogger; prose=19164 (96% of max 19978)
  - era=blogger, archivedAt=2024-09-20T20:05:05Z, local_imgs=1, ext_imgs=0, prose=19164
- **Demoted:**
  - `rhubarb-pudding-recipes-2.md` — era=static, archivedAt=2008-10-15T04:23:46Z, local_imgs=0, ext_imgs=0, prose=19978

### [recipes] rhubarb salad recipes

- **Canonical:** `rhubarb-salad-recipes.md` — mode=era-candidate; era=blogger; prose=3131 (85% of max 3669)
  - era=blogger, archivedAt=2024-06-22T00:21:06Z, local_imgs=1, ext_imgs=0, prose=3131
- **Demoted:**
  - `rhubarb-salad-recipes-2.md` — era=static, archivedAt=2008-10-16T04:31:21Z, local_imgs=0, ext_imgs=0, prose=3669

### [recipes] rhubarb sauce recipes

- **Canonical:** `rhubarb-sauce-recipes.md` — mode=era-candidate; era=blogger; prose=37489 (96% of max 39239)
  - era=blogger, archivedAt=2024-09-20T19:16:45Z, local_imgs=1, ext_imgs=0, prose=37489
- **Demoted:**
  - `rhubarb-sauce-recipes-2.md` — era=static, archivedAt=2008-10-15T04:23:51Z, local_imgs=0, ext_imgs=0, prose=39239

### [recipes] rhubarb tart recipes

- **Canonical:** `rhubarb-tart-recipes.md` — mode=era-candidate; era=blogger; prose=12681 (96% of max 13179)
  - era=blogger, archivedAt=2024-08-07T18:23:50Z, local_imgs=1, ext_imgs=0, prose=12681
- **Demoted:**
  - `rhubarb-tart-recipes-2.md` — era=static, archivedAt=2008-10-16T04:31:26Z, local_imgs=0, ext_imgs=0, prose=13179

### [recipes] rhubarb wine

- **Canonical:** `rhubarb-wine.md` — mode=era-candidate; era=blogger; prose=24547 (100% of max 24590)
  - era=blogger, archivedAt=2024-09-20T21:07:36Z, local_imgs=1, ext_imgs=0, prose=24547
- **Demoted:**
  - `rhubarb-wine-2.md` — era=drupal, archivedAt=2020-02-01T02:18:36Z, local_imgs=0, ext_imgs=0, prose=24590

