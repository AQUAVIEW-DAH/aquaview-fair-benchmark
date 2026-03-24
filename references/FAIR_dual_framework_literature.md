# FAIR Dual-Framework Literature Review

References supporting the FAIR-C (Computational) / FAIR-H (Human) dual-scoring framework.

## Foundational

- **Wilkinson et al. (2016)** "The FAIR Guiding Principles for scientific data management and stewardship." *Scientific Data* 3:160018. doi:10.1038/sdata.2016.18
  - The original FAIR paper. Notes that humans and machines "face distinct barriers" but does not formalize separate assessment dimensions.

- **Wilkinson et al. (2019)** "Evaluating FAIR maturity through a scalable, automated, community-governed framework." *Scientific Data* 6:174. doi:10.1038/s41597-019-0184-5
  - Introduces the FAIR Evaluator. Coins "FAIR for machines" / "FAIR for humans" phrasing. Argues machine FAIRness is foundational: "once data is FAIR for machines, there are myriad tools that can assist in automatically making it FAIR for humans."

## Closest Prior Work

- **Vogt (2023)** "FAIREr: A framework extending FAIR with Explorability." arXiv:2301.04202
  - Proposes adding "cognitive interoperability" as a fifth EOSC interoperability layer. Argues machine-actionability emphasis has overshadowed human-actionability. Augments FAIR rather than splitting it.

- **Vogt (2025)** "The CLEAR Principle for semantic organization of FAIR Digital Objects." *Journal of Biomedical Semantics*. doi:10.1186/s13326-025-00340-7
  - Proposes organizing data into semantically meaningful units for human explorability. Complements machine-oriented FAIR.

- **Vogt et al. (2024)** "Suggestions for extending the FAIR Principles based on a linguistic perspective on semantic interoperability." arXiv:2405.03345
  - "FAIR 2.0" — extends FAIR with semantic interoperability additions bridging human cognition and machine-actionability.

- **Vogt & Mons (2025)** "The Grammar of FAIR: A Granular Architecture of Semantic Units for FAIR Semantics, Inspired by Biology and Linguistics." arXiv:2509.26434
  - Discusses supporting "both human comprehension and machine usability" through granular semantic architecture.

- **Kenney & Read (2024)** "The usability gap in water resources open data." *Journal of the American Water Resources Association (JAWRA)*. doi:10.1111/1752-1688.13153
  - Argues "optimizing and testing for usability and understandability are as central to stakeholder use as FAIR standards are." Positions usability as parallel requirement to FAIR. Directly relevant to environmental/ocean data context.

## Assessment Tools & Frameworks

- **Candela, Mangione & Pavone (2024)** "The FAIR assessment conundrum: Reflections on tools and metrics." *Data Science Journal*. doi:10.5334/dsj-2024-033
  - Reviews 20 FAIR assessment tools and 1180 metrics. Notes tension between machine and human perspectives but does not propose dual-scoring.

- **Krans et al. (2022)** "FAIR assessment tools: evaluating use and performance." *NanoImpact*. doi:10.1016/j.impact.2022.100402
  - Reviews ten FAIR assessment tools. All focus on machine-actionability (F-UJI, FAIR Evaluator, FAIR-Checker).

- **Peng & Berg (2024)** "Harmonizing quality measures of FAIRness assessment towards machine-actionable quality information." *International Journal of Digital Earth*. doi:10.1080/17538947.2024.2390431
  - Consolidated FAIR vocabulary. Mentions "explicit consideration for human users" alongside machine-actionable quality.

## Operational Examples

- **Benis et al. (2025)** "FAIR for humans and machines in omics data." Research Square preprint rs-7820760.
  - Tested repositories using web searches ("FAIR for humans") and API queries ("FAIR for machines") — closest operational example of measuring both, but did not produce formal separate scores.

- **Delavenne et al. (2025)** "Adjusted FAIR principles for livestock production data reusability." *Scientific Data*. doi:10.1038/s41597-025-04785-4
  - Explicitly adjusted machine-oriented FAIR indicators to focus on human-actionability for a specific domain. Closest example of pivoting between orientations, but not a parallel dual-score.

- **Gryk (2022)** "Human readability metric for data file formats." *Balisage Series*.
  - Proposed quantitative "human readability" metric (ratio of meaningful to total characters). Narrow (file format level) but demonstrates the concept of measuring human data experience quantitatively.

## Community & Policy

- **Jacobsen et al. (2020)** "FAIR principles: interpretations and implementation considerations." *Data Intelligence* 2(1-2):10-29. doi:10.3233/DS-190026
  - Discusses machine-actionability as a continuum. States "FAIR is not just about humans."

- **Hong et al. (2020)** "Six Recommendations for Implementation of FAIR Practice." EOSC FAIR Working Group.
  - Community observation: "FAIR for machines is recognised as important, but also seen as a very difficult goal to reach. Sometimes it is perceived as secondary to FAIR for humans."

- **Borycz & Carroll (2020)** "Implementing FAIR data for people and machines: Impacts and implications." *Information Services & Use* 40(3):219-227. doi:10.3233/ISU-200083
  - Frames the duality in the title. Workshop results on practical implementation challenges.

- **Hettne et al. (2020)** "FIP Wizard: Recommendations for FAIR implementation." *Data Science Journal*. doi:10.5334/dsj-2020-040
  - Discusses FAIR for humans and machines at Leiden.

- **Dunning, De Smaele & Bohmer (2017)** "Are the FAIR data principles fair?" *International Journal of Digital Curation*. doi:10.2218/ijdc.v12i2.567
  - Early critique. "Both machines and humans should be enabled to find, access, interoperate, and reuse."

## The Gap

No published work produces a **parallel dual-scoring instrument** — separate FAIR-C and FAIR-H scores applied to the same datasets. The distinction is widely acknowledged but never operationalized as two measurement instruments. Existing tools measure machine-actionability (automated) or human usability (manual/survey) but never both in a unified framework.

Our contribution: formalize the split, build both instruments, and demonstrate empirically that the two dimensions diverge on the same data.
