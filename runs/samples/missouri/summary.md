# Solution summary: TR202504 RFP Using AI /ML to Write Legal Land Descriptions

- **Source:** data/rfps/missouri.pdf
- **Run:** missouri
- **Generated:** 2026-10-31T00:24:00.022154+00:00
- **Model:** deepseek:deepseek-flash

## Problem statement

### Client situation

- The issuing body is the Missouri Highways and Transportation Commission (MHTC), which is procuring the study on behalf of the Missouri Department of Transportation (MoDOT), with MoDOT's Right of Way staff reviewing drafts. ((A) Request for Proposal, p. 5 [S8.1]; (B) Background, p. 5 [S9.1])
- MoDOT's Right of Way function must describe every realty right it acquires, conveys or leases by metes and bounds, lot calls or 1/4-1/4 calls, reciting specific rights when less than fee simple title is taken. ((B) Background, p. 5 [S9.1])
- Descriptions prepared for MHTC must meet the MoDOT Engineering Policy Guide (EPG) Section 236.4.6.2, and a professional land surveyor must review each description against the right of way plans before a deed is presented to the grantor. ((B) Background, p. 5 [S9.1])
- The business driver is to determine whether Artificial Intelligence and Machine Learning can produce a usable "first draft" legal land description from MHTC parameters that MoDOT Right of Way staff would then review and edit. ((B) Background, p. 5 [S9.1])
- The work is coordinated by the Research Unit of MoDOT's Construction and Materials Division, and the Offeror must fully coordinate its activities with that Division. (Front matter, pp. 1-2 [S1.1]; (A) MHTC's Representative, p. 13 [S49.1])
- MoDOT's Research Director, Jen Harper, is MHTC's designated representative for administering the agreement and may delegate authority to others. ((A) MHTC's Representative, p. 13 [S49.1]; Front matter, pp. 1-2 [S1.1])
- MoDOT operates on a fiscal year running July 1 to June 30, which drives the quarterly reporting cycle submitted to FHWA. ((C) Fiscal Year, p. 5 [S10.1]; (G) Project Schedule, pp. 6-7 [S15.1])

### Goal

- The client wants a research study, TR202504 "Using AI/ML to Write Legal Land Descriptions," that determines the usefulness of AI/ML for generating first-draft legal land descriptions. ((A) Request for Proposal, p. 5 [S8.1]; (B) Background, p. 5 [S9.1])
- The Offeror must deliver a proof of concept demonstrating how the chosen technology creates draft legal land descriptions across a variety of properties, with MoDOT reviewing the drafts and giving improvement feedback. (Task 3c: Proof of Concept that AI/ML Can Develop Legal Land Descriptions, p. 9 [S23.1]; Task Deliverables, p. 6 [S14.1])
- The Offeror must name the program it will use to develop the LLDs before proof-of-concept work begins, and MoDOT Information Systems must approve it before Task 3c can proceed. (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1])
- Deliverables include a literature review of other state DOT practices using AI/ML for right-of-way purposes, a Data Management Plan, training and a user manual for ROW staff, a draft and final report, a 1-2 page research summary, and a presentation to MoDOT staff. (Task 2: Literature Review, p. 8 [S20.1]; Task 1: Project Management, p. 8 [S19.1]; Task 4: Training and User Manual, p. 9 [S24.1]; Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1]; Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1])
- The contract period is 15 months, with the schedule estimated to start November 1, 2024 and the final invoice due and contract ending February 2, 2026. ((D) Contract Period and Budget, p. 5 [S11.1]; (G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])
- Key milestones are a kick-off meeting on 11/15/2024, the Data Management Plan on 12/4/2024, MoDOT-supplied example LLDs on 12/20/2024, an AI/ML demonstration on 4/25/2025, training and manual on 7/25/2025, an interim presentation on 9/15/2025, the draft final report on 11/3/2025, and the final report on 1/1/2026. ((G) Project Schedule, p. 7 [S15.2])
- The Offeror must provide monthly e-mail and phone updates, quarterly status meetings with minutes, and quarterly written updates due by the last working day of March, June, September and December. ((G) Project Schedule, pp. 6-7 [S15.1]; Task 1: Project Management, p. 8 [S19.1])

### Success criteria

- Proposals are due by 10 a.m. Central on August 21, 2024 to MoDOTResearchRFP@modot.mo.gov, with receipt acknowledged by noon the same day. ((E) RFP Schedule, pp. 5-6 [S12.1]; (1) Pricing and Signature, p. 10 [S30.1])
- All questions and comments must go only to MoDOTResearchRFP@modot.mo.gov by 4 p.m. Central on July 17, 2024; contacting MoDOT employees by any other method is cause for disqualification. ((E) RFP Schedule, pp. 5-6 [S12.1]; (4) Clarification of Requirements, p. 10 [S33.1])
- MoDOT posts its responses to questions publicly on 7/31/2024 and notifies submitters of project selection or interviews on 9/18/2024. ((E) RFP Schedule, pp. 5-6 [S12.1])
- Award goes to the Offeror providing the best proposal, with responsiveness determined first and then evaluation by the Technical Advisory Committee against criteria the RFP does not list or weight. ((1) Evaluation Factors, p. 11 [S41.1])
- The proposal must include a narrative Work Plan of no more than 10 pages at 12-point font or larger, covering all Section 2 items and recognizing MoDOT's ultimate authority to approve work plans. ((2) Work Plan, p. 10 [S36.1])
- The proposal must document experience delivering these services in the past three years, list at least three client references from the past three years, and identify any Sub-Offerors with full contact information. ((4) Experience, p. 11 [S38.1]; (5) References, p. 11 [S39.1]; (3) Personnel, pp. 10-11 [S37.1])
- The proposal must be submitted as one combined PDF in a fixed order: Proposal Submission Form, optional one-page cover letter, body of proposal, personnel, organization experience, team member experience, and client references. ((5) References, p. 11 [S39.1])
- Failure to submit all data required under paragraph (B) is deemed sufficient cause for disqualification. ((2) Submission of All Data Required, p. 10 [S31.1])

### Constraints

- Services are capped at a not-to-exceed amount of $175,000, and the cost estimate must be entered on the Section (4) Price Page line items for Salaries, Benefits, Operating Expense, Facilities and Administration, Miscellaneous and Total. ((A) Services, p. 8 [S17.1])
- Any application must be built on .NET 6.0 or above (or .NET Framework 4.8 or above), use MVC, Razor Pages or Web API, and be written in C#, JavaScript, CSS, HTML or Python, with Python reserved for ESRI scripts and small one-time uses unless the Information Systems Best Practices Review Team approves larger use. ((Y) Information Technology, pp. 17-18 [S73.1]; (Y) Information Technology, p. 18 [S73.2])
- No third-party tool or software that places a licensing responsibility on MoDOT may be used without prior review and approval by the Information Systems Best Practices Review Team and IS management. ((Y) Information Technology, pp. 17-18 [S73.1])
- Applications must be web-based, require no client-side software beyond a modern browser (no Java Applets or Silverlight), run on Oracle 19C or a supported SQL Server version, and meet WCAG 2.1 AA and the State of Missouri accessibility standard. ((Y) Information Technology, p. 18 [S73.2])
- No personally identifiable information may be stored in any database table without a specific business need and approval from the IS Cyber Security Team. ((Y) Information Technology, p. 18 [S73.2])
- A Data Management Plan is due to MoDOT within 2 weeks after the kick-off meeting and must describe data formats and how platform-independent, non-proprietary formats will be used. (Task 1: Project Management, p. 8 [S19.1])
- All documents, reports and exhibits the Offeror produces at MHTC's direction, and all information MHTC supplies, remain MHTC property, and records must be kept available to MHTC and the Missouri State Auditor for three years after final payment. ((Q) Ownership of Reports, p. 16 [S65.1]; (U) Maintain Papers, p. 16 [S69.1])
- Offerors are encouraged to reach 10% MBE and 5% WBE participation while remaining fully liable for subcontractor performance, and may be asked before signing to provide insurance of at least $500,000 per person and $3,000,000 per occurrence for general and automobile liability plus Missouri workers' compensation. ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1]; (X) Insurance, p. 17 [S72.1])
- The Offeror must submit the Exhibit A sworn affidavit of E-Verify enrollment and no unauthorized alien employment, and sole proprietorships or partnerships must also submit the Exhibit B affidavit of lawful presence. ((K) Non-employment of Unauthorized Aliens, pp. 14-15 [S59.1]; (L) Proof of Lawful Presence for Sole Proprietorships and Partnerships, p. 15 [S60.1])
- The RFP refers bidders to documents it does not include: the Standard Research Agreement, the Proposal Submission Form, the Price Page template, the Publication Guidelines and research summary template, all posted at https://www.modot.org/information-researchers. ((D) Contract Period and Budget, p. 5 [S11.1]; (1) Proposal Submission Form, p. 10 [S35.1]; (1) Cost Estimate, p. 11 [S45.1]; Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1]; Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1])

## Requirements

123 requirements: 104 mandatory, 16 desired, 3 optional.

### Functional (17)

- **R010** (mandatory) The bidder must be a qualified organization proposing to conduct the TR202504 "Using AI/ML to Write Legal Land Descriptions" study for the MHTC and Missouri Department of Transportation (MoDOT).
  > "This document constitutes an RFP from qualified organizations to conduct the TR202504, "Using AI/ML to Write Legal Land Descriptions" study for the MHTC and Missouri Department of Transportation (MoDOT)." ((A) Request for Proposal, p. 5 [S8.1])
- **R014** (mandatory) The AI/ML solution must produce a "first draft" of the legal land description (LLD) using the MHTC parameters, which MoDOT's Right of Way staff can then review and edit.
  > "The goal of this research project is to determine the usefulness of Artificial Intelligence (AI) and Machine Learning (ML) to develop a "first draft" of the legal land description (LLD) using the MHTC parameters." ((B) Background, p. 5 [S9.1])
- **R023** (mandatory) The Offeror must demonstrate the AI writing a legal land description.
  > "Demonstration of AI writing a legal land description" (Task Deliverables, p. 6 [S14.1])
- **R031** (mandatory) E-mail and phone communications with MoDOT contacts are required on a monthly basis to provide ongoing updates of progress. _(merged from R032)_
  > "E-mail and phone communications with MoDOT contacts are required to provide ongoing updates of progress." ((G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])
- **R043** (mandatory) The Offeror must facilitate a kick-off meeting with MoDOT to review the work plan, scope and schedule and to establish a protocol for regular ongoing communications and coordination with the team. _(merged from R033)_
  > "The Offeror will facilitate a kick-off meeting with MoDOT to review the work plan, scope, and schedule; and establish a protocol for regular ongoing communications and coordination with the team." (Task 1: Project Management, p. 8 [S19.1]; (G) Project Schedule, p. 7 [S15.2])
- **R044** (mandatory) The Offeror must schedule and conduct quarterly project status meetings reviewing progress for the previous period and anticipated work for the next period, held in person or online.
  > "The Offeror will schedule and conduct quarterly project status meetings to review progress for the previous period and anticipated work for the next period." (Task 1: Project Management, p. 8 [S19.1])
- **R045** (mandatory) The Offeror must develop minutes for the kick-off meeting and for each quarterly status meeting. _(merged from R022)_
  > "The Offeror will also develop minutes for the kick-off meeting and each of the quarterly status meetings." (Task 1: Project Management, p. 8 [S19.1]; Task Deliverables, p. 6 [S14.1])
- **R046** (mandatory) The finalized work plan must detail implementation of the project tasks as well as the resources and schedule required to carry them out.
  > "The finalized work plan will detail implementation of the following tasks as well as the resources and schedule required to carry them out." (Task 1: Project Management, p. 8 [S19.1])
- **R050** (mandatory) The vendor must conduct a thorough literature search and review of other state DOT practices using AI/ML for right-of-way (ROW) purposes.
  > "A thorough literature search and review of other state DOT practices using AI/ML for ROW purposes conducted." (Task 2: Literature Review, p. 8 [S20.1])
- **R053** (mandatory) The Offeror must demonstrate how its technology will create draft legal land descriptions for a variety of properties.
  > "The Offeror will demonstrate how the technology will create draft legal land descriptions on a variety of properties." (Task 3c: Proof of Concept that AI/ML Can Develop Legal Land Descriptions, p. 9 [S23.1])
- **R055** (mandatory) The training must include a user manual for staff to reference.
  > "The training will also have a user manual for staff to reference." (Task 4: Training and User Manual, p. 9 [S24.1])
- **R056** (mandatory) The Offeror must prepare a draft Synthesis Report and Research Summary along with all accompanying documentation identified as beneficial during the study. _(merged from R060)_
  > "The Offeror will prepare a draft Synthesis Report and Research Summary along with all accompanying documentation identified as beneficial during the study." (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1]; Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1])
- **R061** (mandatory) The Offeror must provide a 1-2 page research summary stating the project objectives, findings and conclusions. _(merged from R057)_
  > "The Offeror will provide a 1-2 page research summary that states the project objectives, findings and conclusions." (Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1]; Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **R062** (mandatory) The Offeror must provide a presentation for MoDOT staff summarizing important or significant details of the project.
  > "A presentation for MoDOT staff summarizing important or significant details of the project must be provided." (Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1])
- **R064** (mandatory) The Offeror must consult MHTC's representative regarding any concerns involved with the administration of the services provided under this RFP.
  > "The Offeror will consult MHTC's representative regarding any concerns involved with the administration of the services provided pursuant to this RFP." ((C) Administration of Program, p. 9 [S27.1])
- **R099** (mandatory) The Offeror shall fully coordinate its activities for MHTC with those of the Construction and Materials Division.
  > "The Offeror shall fully coordinate its activities for MHTC with those of the Construction and Materials Division." ((A) MHTC's Representative, p. 13 [S49.1])
- **R100** (mandatory) The Offeror shall make advice and information on matters covered by the Agreement available to the Construction and Materials Division throughout the effective period of the Agreement.
  > "advice and information on matters covered by the Agreement shall be made available by the Offeror to the Construction and Materials Division throughout the effective period." ((A) MHTC's Representative, p. 13 [S49.1])

### Technical (18)

- **R011** (mandatory) Property descriptions prepared on behalf of the MHTC must be prepared in a manner that meets the requirements outlined in the MoDOT Engineering Policy Guide (EPG) Section 236.4.6.2.
  > "Property descriptions prepared on behalf of the MHTC must be prepared in a manner that meets the following requirements as outlined in the MoDOT Engineering Policy Guide (EPG)" ((B) Background, p. 5 [S9.1])
- **R012** (mandatory) Realty rights acquired or conveyed by the MHTC must be described using the metes and bounds method, unless the property is acquired in its entirety.
  > "realty rights being acquired or conveyed by the MHTC must be described using the metes and bounds method, unless the property is acquired in its entirety" ((B) Background, p. 5 [S9.1])
- **R013** (mandatory) When a property is acquired in its entirety, the property description must be written exactly as it appears on the last deed of record for the subject property.
  > "When acquiring a property in its entirety, the property description shall be written exactly as it appears on the last deed of record for the subject property." ((B) Background, p. 5 [S9.1])
- **R048** (mandatory) The Data Management Plan must describe the anticipated format(s) the Offeror's data and related files will use.
  > "The plan will describe the anticipated format(s) your data and related files will use." (Task 1: Project Management, p. 8 [S19.1])
- **R049** (desired) The Data Management Plan should address how the Offeror will use platform-independent and non-proprietary formats to ensure maximum future utility of the data.
  > "The DMP should address how the Offeror will use platform-independent and non-proprietary formats to ensure maximum utility of the data in the future." (Task 1: Project Management, p. 8 [S19.1])
- **R130** (mandatory) All applications must be developed using one of the technologies approved in the Approved Technologies section of the RFP.
  > "All applications must be developed using one of the approved technologies stated in the Approved Technologies section of this document." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R131** (desired) A currently supported .NET 6.0 or above release should be used unless there is a specific need for .NET Framework.
  > "A currently supported .NET 6.0 or above release should be used unless there is a specific need for .NET Framework." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R132** (mandatory) If .NET Framework is required, a currently supported 4.8 release or above must be used.
  > "If a .NET Framework is required, a currently supported 4.8 release or above will be used." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R133** (mandatory) Web applications must use either the MVC, Razor Pages or Web API framework.
  > "Web applications must use either the MVC, Razor Pages or Web API framework." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R134** (desired) Library dependencies used in the application should be reviewed and updated on an annual basis.
  > "Library dependencies used in the application should be reviewed/updated on an annual basis." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R136** (desired) New development should use the approved programming languages: C#, JavaScript, CSS, HTML, and Python.
  > "The following are the approved programming languages that should be used for new development." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R137** (mandatory) Python is reserved for ESRI scripts and other small one-time uses, and large-scale use of Python requires approval of the Information Systems (IS) Best Practices Review Team (BRPT).
  > "Python is reserved for use in ESRI scripts and other small one-time uses. Large scale use of Python requires the approval of the Information Systems (IS) Best Practices Review Team (BRPT)." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R138** (desired) For platforms other than ArcGIS Desktop, ArcGIS Pro and ArcGIS Enterprise, version 3.x of Python from www.python.org should be used.
  > "For other platforms a version 3.x of Python from www.python.org should be used." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R139** (desired) All customer applications should be web-based browser applications.
  > "All customer applications should be Web Based, browser applications." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R140** (desired) Applications should be tested and designed to use the latest IS-approved browser(s) at a minimum. _(merged from R141)_
  > "Applications should be tested and designed to use the latest IS approved browser(s), at a minimum." ((Y) Information Technology, pp. 17-18 [S73.1]; (Y) Information Technology, p. 18 [S73.2])
- **R142** (desired) No client-side software other than a modern browser (e.g., no Java Applets, no Silverlight) may be required to run the web application.
  > "No client-side software, other than a modern browser, should be required to run the web application." ((Y) Information Technology, p. 18 [S73.2])
- **R143** (mandatory) On-premise database deployments must run on Oracle 19C. _(conflicts with R144)_
  > "On premise database deployments shall be ran on:" ((Y) Information Technology, p. 18 [S73.2])
- **R144** (desired) The application must be designed and maintained to run on the latest supported version of Microsoft SQL Server, with SQL Server 2016 or higher permitted only if approved by the MoDOT IS Data Service Management team. _(conflicts with R143)_
  > "The application should be designed and maintained to run on the latest supported version of SQL server." ((Y) Information Technology, p. 18 [S73.2])

### Security and compliance (7)

- **R116** (mandatory) The business entity must provide acceptable enrollment and participation documentation consisting of a completed copy of the E-Verify Memorandum of Understanding (MOU) for the employees proposed to work in connection with the services. _(merged from R115)_
  > "The business entity must affirm its enrollment and participation in the E-Verify federal work authorization program with respect to the employees proposed to work in connection with the services requested herein by providing acceptable enrollment and participation documentation consisting of **completed** copy of the E-Verify Memorandum of Understanding (MOU)." ((K) Non-employment of Unauthorized Aliens, pp. 14-15 [S59.1])
- **R117** (mandatory) The business entity must, by sworn affidavit, affirm that it does not knowingly employ any person who is an unauthorized alien in connection with the contracted services.
  > "By sworn affidavit, affirm that it does not knowingly employ any person who is an unauthorized alien in connection with the contracted services." ((K) Non-employment of Unauthorized Aliens, pp. 14-15 [S59.1])
- **R121** (mandatory) The Offeror shall not disclose confidential factual matters provided by MHTC to third parties except as required by statute, ordinance, or court order, or as authorized by MHTC's representative.
  > "The Offeror shall not disclose to third parties confidential factual matters provided except as may be required by statute, ordinance, or order of court, or as authorized by MHTC's representative." ((R) Confidentiality, p. 16 [S66.1])
- **R122** (mandatory) The Offeror shall notify MHTC immediately of any request for such confidential information.
  > "The Offeror shall notify MHTC immediately of any request for such information." ((R) Confidentiality, p. 16 [S66.1])
- **R145** (mandatory) No Personal Identifiable Information (PII) may be stored in any database table unless the application has a specific business need for that data.
  > "No Personal Identifiable Information (PII) can be stored in any database table unless the application has a specific business need to use that data." ((Y) Information Technology, p. 18 [S73.2])
- **R146** (mandatory) All PII data that is stored must be approved by the IS Cyber Security Team.
  > "All PII data that is stored must have approval from the IS Cyber Security Team." ((Y) Information Technology, p. 18 [S73.2])
- **R147** (mandatory) All web applications must meet the standards of the State of Missouri's Accessibility Standard, which is based on Section 508 of the Rehabilitation Act (as amended) and the Web Content Accessibility Guidelines. _(merged from R148)_
  > "All web applications must meet the standards established in State of Missouri's Accessibility Standard, which is based on Section 508 of the Rehabilitation Act (as amended) and Web Content Accessibility Guidelines." ((Y) Information Technology, p. 18 [S73.2])

### Legal and contractual (22)

- **R097** (mandatory) The awarded contract must incorporate the contract provisions specified in this RFP, which will also appear in the post-award negotiated contract.
  > "These same contract provisions will appear in the post-award negotiated contract." (SECTION (5): AGREEMENT REQUIREMENTS, p. 13 [S48.1])
- **R098** (mandatory) The Offeror must accept that the award is subject to a post-award negotiated contract and that MHTC may cancel the award and select a different Offeror if the parties cannot agree on the post-award contract terms.
  > "If the parties are unable to agree to terms in the post-award contract, MHTC shall reserve the right to cancel the award of the RFP and contract and select a different Offeror." (SECTION (5): AGREEMENT REQUIREMENTS, p. 13 [S48.1])
- **R101** (mandatory) The Offeror must not release any material or reports it prepares to the public without the prior consent of MHTC's representative.
  > "No material or reports prepared by the Offeror shall be released to the public without the prior consent of MHTC's representative." ((B) Release to Public, p. 13 [S50.1])
- **R102** (mandatory) The Offeror shall not assign, delegate, or novate any interest in the services to be provided without the prior written consent of MHTC's representative.
  > "The Offeror shall not assign or delegate any interest, and shall not transfer any interest in the services to be provided (whether by assignment, delegation, or novation) without the prior written consent of MHTC's representative." ((C) Assignment, p. 13 [S51.1])
- **R104** (mandatory) The Offeror must accept that written clarifications issued by MHTC govern over conflicting requirements in the RFP or in the Offeror's proposal.
  > "MHTC reserves the right to clarify any relationship in writing and such written clarification shall govern in case of conflict with the applicable requirements stated in the RFP or the Offeror's proposal." ((E) Components of Agreement, p. 13 [S53.1])
- **R105** (mandatory) Any change to the Agreement, whether by modification or supplementation, must be accompanied by a formal contract amendment signed and approved by the duly authorized representative of the Offeror and MHTC.
  > "Any change in the Agreement, whether by modification or supplementation, must be accompanied by a formal contract amendment signed and approved by the duly authorized representative of the Offeror and MHTC." ((F) Amendments, p. 13 [S54.1])
- **R110** (mandatory) The Offeror remains ultimately responsible and liable to MHTC for the complete, accurate and professional quality and performance of the services regardless of any subcontractors or suppliers it uses.
  > "the Offeror ultimately remains responsible and liable to MHTC for the complete, accurate and professional quality/performance of these services" ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])
- **R111** (mandatory) The Offeror shall comply with all provisions of Missouri Executive Order 07-13 (issued March 6, 2007) regarding not employing individuals who are not eligible to work in the United States.
  > "The Offeror shall comply with all the provisions of Executive Order 07-13, issued by the Honorable Matt Blunt, Governor of Missouri, on the sixth (6<sup>th</sup> ) day of March, 2007." ((I) Executive Order, p. 14 [S57.1])
- **R112** (mandatory) By signing the Agreement, the Offeror certifies that any employee assigned to perform services under the contract is eligible and authorized to work in the United States in compliance with federal law.
  > "By signing this Agreement, the Offeror hereby certifies that any employee of the Offeror assigned to perform services under the contract is eligible and authorized to work in the United States in compliance with federal law." ((I) Executive Order, p. 14 [S57.1])
- **R113** (mandatory) The Offeror must include the provisions of Section (3), paragraph I of the Agreement in every subcontract.
  > "The Offeror shall include the provisions of Section (3), paragraph I of this Agreement in every subcontract." ((J) Incorporation of Provisions, p. 14 [S58.1])
- **R114** (mandatory) The Offeror must take such action with respect to any subcontract as the Commission may direct as a means of enforcing such provisions, including sanctions for noncompliance.
  > "The Offeror shall take such action with respect to any subcontract as the Commission may direct as a means of enforcing such provisions, including sanctions for noncompliance." ((J) Incorporation of Provisions, p. 14 [S58.1])
- **R120** (mandatory) All documents, reports, exhibits and other deliverables produced by the Offeror at the direction of MHTC's representative, along with information supplied by MHTC's representative, shall remain the property of MHTC.
  > "All documents, reports, exhibits, etc. produced by the Offeror at the direction of MHTC's representative and information supplied by MHTC's representative shall remain the property of MHTC." ((Q) Ownership of Reports, p. 16 [S65.1])
- **R123** (mandatory) The Offeror must maintain all working papers and records relating to the Agreement.
  > "The Offeror must maintain all working papers and records relating to the Agreement." ((U) Maintain Papers, p. 16 [S69.1])
- **R124** (mandatory) The Offeror's records must be made available at no charge to MHTC and/or the Missouri State Auditor at all reasonable times during the term of the Agreement and any extension, and for three (3) years from the date of final payment.
  > "These records must be made available at all reasonable times at no charge to MHTC and/or the Missouri State Auditor during the term of the Agreement and any extension thereof, and for three (3) years from the date of final payment made under the Agreement." ((U) Maintain Papers, p. 16 [S69.1])
- **R125** (optional) MHTC's representative may reproduce and use any products derived from the Offeror's work without payment of royalties or fees.
  > "MHTC's representative shall have the right to reproduce and/or use any products derived from the Offeror's work without payment of any royalties, fees, etc." ((U) Maintain Papers, p. 16 [S69.1])
- **R126** (optional) Prior to contract signing, the Offeror may be asked to demonstrate its ability to provide certificates of insurance meeting or approaching the specified coverages.
  > "Prior to contract signing, the Offeror may be asked about its ability to provide certificates of insurance which meet, or approach, the following coverages:" ((X) Insurance, p. 17 [S72.1])
- **R127** (mandatory) The Offeror must be able to provide General Liability insurance of not less than $500,000 for any one person in a single accident or occurrence and not less than $3,000,000 for all claims arising out of a single occurrence.
  > "General Liability Not less than $500,000 for any one person in a single accident or occurrence, and not less than $3,000,000 for all claims arising out of a single occurrence;" ((X) Insurance, p. 17 [S72.1])
- **R128** (mandatory) The Offeror must be able to provide Automobile Liability insurance of not less than $500,000 for any one person in a single accident or occurrence and not less than $3,000,000 for all claims arising out of a single occurrence.
  > "Automobile Liability Not less than $500,000 for any one person in a single accident or occurrence, and not less than $3,000,000 for all claims arising out of a single occurrence;" ((X) Insurance, p. 17 [S72.1])
- **R129** (mandatory) The Offeror must be able to provide a Missouri State Workmen's Compensation policy or equivalent in accordance with state law.
  > "Missouri State Workmen's Compensation policy or equivalent in accordance with state law." ((X) Insurance, p. 17 [S72.1])
- **R135** (mandatory) Vendors may not use third-party tools or software that would place a licensing responsibility on MoDOT without prior review and approval by the Information Systems Best Practices Review Team (BRPT) and IS management.
  > "Vendors may not use third-party tools or software which would place a licensing responsibility on MoDOT without prior review and approval of the tools and or software by the Information Systems Best Practices Review Team (BRPT) and IS management." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R149** (mandatory) The vendor must never use text, diagrams, photographs, audio, multimedia, program source code, script or graphics from another author's web pages unless the author explicitly permits free copying or appropriate arrangements are made with the author.
  > "Never use text, diagrams, photographs, audio, multimedia, program source code, script or graphics from another author's web pages unless the author explicitly states it may be freely copied or you make appropriate arrangements with the author." ((Y) Information Technology, p. 18 [S73.2])
- **R150** (mandatory) Vendor logos, branding or other company endorsements must not appear in the application where a supported, licensed option exists to eliminate them from the display.
  > "Vendor logos, branding, or other company endorsements must not appear if there is a supported option, and licensed way to eliminate them from the display." ((Y) Information Technology, p. 18 [S73.2])

### Timeline (15)

- **R005** (mandatory) Proposals must be submitted within the RFP's stated submission deadlines, as time is of the essence.
  > "Time is of the essence for responding to the RFP within the submission deadlines." (INTRODUCTION, p. 4 [S4.1])
- **R015** (mandatory) The contract period will run for 15 months.
  > "The contract period will run for 15 months." ((D) Contract Period and Budget, p. 5 [S11.1])
- **R016** (mandatory) All RFP events must occur between 7:30 a.m. and 4 p.m. Central time.
  > "The time of day for the following events shall be between 7:30 a.m. and 4 p.m., Central." ((E) RFP Schedule, pp. 5-6 [S12.1])
- **R028** (mandatory) Quarterly updates on work accomplished during the quarter must be submitted on or before the last working day of March, June, September, and December for the duration of the project. _(merged from R029)_
  > "Quarterly updates on work accomplished during the quarter are due on or before the last working day of March, June, September, and December during the course of the project." ((G) Project Schedule, pp. 6-7 [S15.1])
- **R030** (mandatory) An interim presentation must be scheduled near the mid-point of the project to update MoDOT on progress and project direction. _(conflicts with R037)_
  > "An interim presentation shall be scheduled near the mid-point of the project to update MoDOT on the progress and the direction of the project." ((G) Project Schedule, pp. 6-7 [S15.1])
- **R034** (mandatory) The data management plan is due on 12/4/2024. _(conflicts with R047)_
  > "The data management plan is due." ((G) Project Schedule, p. 7 [S15.2])
- **R035** (mandatory) The Offeror must present on 4/25/2025 how the AI/ML will create draft LLDs and incorporate MoDOT feedback for improvement.
  > "The Offeror presents how the AI/ML will create draft LLDs." ((G) Project Schedule, p. 7 [S15.2])
- **R036** (mandatory) By 7/25/2025, after adjustments are made to the tool, the Offeror must create a manual and provide training to ROW staff. _(merged from R024, R054)_
  > "After adjustments are made to the tool, the Offeror will create a manual and<br>provide training to ROW staff." ((G) Project Schedule, p. 7 [S15.2]; Task Deliverables, p. 6 [S14.1]; Task 4: Training and User Manual, p. 9 [S24.1])
- **R037** (mandatory) An interim presentation must be completed by 9/15/2025. _(conflicts with R030)_
  > "Interim presentation must be done by this date." ((G) Project Schedule, p. 7 [S15.2])
- **R038** (mandatory) The draft final report, summary report, and user manual are due on 11/3/2025. _(merged from R025)_
  > "Draft final report, summary report, and user manual are due." ((G) Project Schedule, p. 7 [S15.2]; Task Deliverables, p. 6 [S14.1])
- **R039** (mandatory) The final report, summary report, presentation, and user manual are due on 1/1/2026, approximately one month before the end of the contract so all billing can be completed. _(merged from R026)_
  > "Final report, summary report, presentation, and user manual due." ((G) Project Schedule, p. 7 [S15.2]; Task Deliverables, p. 6 [S14.1])
- **R040** (mandatory) The final invoice is due and the contract ends on 2/2/2026.
  > "Final invoice due and contract ends." ((G) Project Schedule, p. 7 [S15.2])
- **R047** (mandatory) The Offeror must submit a Data Management Plan (DMP) to MoDOT within 2 weeks after the project kick-off meeting. _(conflicts with R034)_
  > "The Offeror is required to submit a Data Management Plan (DMP) to MoDOT within 2 weeks after the project kick-off meeting." (Task 1: Project Management, p. 8 [S19.1])
- **R052** (mandatory) MoDOT Information Systems must approve the named LLD development program before the Offeror may move forward with Task 3c.
  > "MoDOT Information Systems must give approval before moving forward with Task 3c" (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1])
- **R073** (mandatory) Questions must be submitted by the date and time listed in section 1E.
  > "by the date and time listed in section 1E" ((4) Clarification of Requirements, p. 10 [S33.1])

### Budget and pricing (6)

- **R007** (mandatory) The Offeror must agree to provide the services at the fees quoted, under the terms of this RFP.
  > "The Offeror agrees to provide the services at the fees quoted, under the terms of this RFP." (PROPOSAL, p. 4 [S5.1])
- **R041** (mandatory) The successful Offeror shall provide the services described in the scope of work for a total not to exceed $175,000.
  > "The successful Offeror shall provide the following services not to exceed $175,000." ((A) Services, p. 8 [S17.1])
- **R091** (mandatory) The Offeror must submit a proposed cost estimate covering all services defined in the Scope of Work. _(merged from R006, R094)_
  > "The Offeror must submit a proposed cost estimate for all services defined in the Scope of Work." ((1) Cost Estimate, p. 11 [S45.1]; PROPOSAL, p. 4 [S5.1]; (A) Cost Estimate, p. 12 [S47.1])
- **R092** (mandatory) The cost estimate must be shown on Section (4), Price Page, of the proposal. _(merged from R093)_
  > "This estimate must be shown on Section (4), Price Page, of this proposal" ((1) Cost Estimate, p. 11 [S45.1])
- **R095** (mandatory) The Cost Estimate must be broken out into the line items Salaries, Benefits, Operating Expense, Facilities and Administration (F&A) Cost, Miscellaneous, and Total.
  > "Facilities and Administration (F&A)<br>Cost" ((A) Cost Estimate, p. 12 [S47.1])
- **R096** (mandatory) Miscellaneous costs must be itemized, with an additional sheet attached if needed.
  > "Miscellaneous (list-attach additional<br>sheet if needed)" ((A) Cost Estimate, p. 12 [S47.1])

### Submission (34)

- **R001** (mandatory) Proposals for project TR202504 must be submitted to MoDOTResearchRFP@modot.mo.gov by August 21, 2024 at 10 a.m. Central. _(merged from R020, R065, R068)_
  > "Please submit all proposals to **<u>MoDOTResearchRFP@modot.mo.gov</u>** by **August 21, 2024** at **10 a.m. (Central)** ." (Front matter, pp. 1-2 [S1.1]; (E) RFP Schedule, pp. 5-6 [S12.1]; (1) Pricing and Signature, p. 10 [S30.1])
- **R008** (mandatory) The proposal must be signed by an authorized signatory of the Offeror and dated.
  > "Authorized Signature of Offeror: ___________________________________________________" (PROPOSAL, p. 4 [S5.1])
- **R009** (mandatory) The proposal must include the Offeror's printed or typed name, mailing address, city, state, zip, telephone, fax and electronic mail address.
  > "Printed or Typed Name: __________________________________________________________ Mailing Address: _______________________________________________________________ City: __________________________ State: ______________________ Zip: _______________ Telephone: ________________________________ Fax: _______________________________ Electronic Mail Address: _________________________________________________________" (PROPOSAL, p. 4 [S5.1])
- **R017** (mandatory) Comments or questions about the RFP must be submitted by email to MoDOTResearchRFP@modot.mo.gov. _(merged from R072)_
  > "Comments or questions must be submitted to<br>**MoDOTResearchRFP@modot.mo.gov**." ((E) RFP Schedule, pp. 5-6 [S12.1]; (4) Clarification of Requirements, p. 10 [S33.1])
- **R018** (mandatory) Email to MoDOTResearchRFP@modot.mo.gov is the only acceptable method of contact regarding the RFP, and contacting MoDOT employees by other methods is prohibited and is cause for disqualification. _(merged from R019)_
  > "This is the only acceptable method for contact regarding the RFP and<br>contacting MoDOT employees via other methods is prohibited." ((E) RFP Schedule, pp. 5-6 [S12.1])
- **R021** (mandatory) A proposal is not considered submitted until the submitter receives notification of receipt from MoDOT.
  > "Do<br>not consider your proposal submitted until you receive notification of receipt." ((E) RFP Schedule, pp. 5-6 [S12.1])
- **R027** (mandatory) The proposal must include a work plan with a proposed timeline. _(merged from R002, R003, R004)_
  > "Proposals need to include a work plan with a proposed timeline." ((G) Project Schedule, pp. 6-7 [S15.1]; Front matter, pp. 1-2 [S1.1])
- **R042** (mandatory) The Offeror must provide Construction and Materials with an electronic copy of a program proposal that will help bring the project to successful completion.
  > "The Offeror will provide Construction and Materials an electronic copy of a program proposal which will help bring the project to its successful completion." ((B) Specific Requirements, p. 8 [S18.1])
- **R051** (mandatory) Before work begins on the proof of concepts, the Offeror must provide the name of the program used to develop the LLDs.
  > "Before work begins on the proof of concepts, the Offeror will provide the name of the program used to develop the LLDs." (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1])
- **R058** (mandatory) The final report must include a completed Technical Report Documentation page.
  > "A final report must include a completed Technical Report Documentation page." (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **R063** (mandatory) The final report and research summary must follow the Publications Guidelines. _(merged from R059)_
  > "Please refer to the **Publications Guidelines** for the report and research summary, which can be found on the website." (Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1]; Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **R066** (optional) Any form in the RFP containing a signature line, along with any amendments and pricing pages, may be electronically signed or manually signed, scanned and returned as part of the proposal.
  > "Any form containing a signature line in this RFP and any amendments, pricing pages, etc., can be electronically signed or manually signed and scanned and returned as part of the proposal." ((1) Pricing and Signature, p. 10 [S30.1])
- **R067** (mandatory) The proposal must reference the project number and title because more than one RFP may be due at one time.
  > "Please reference the project number and title since more than one RFP may be due at one time." ((1) Pricing and Signature, p. 10 [S30.1])
- **R069** (mandatory) The Offeror must submit all data required in paragraph (B) of the RFP for its proposal to be evaluated and considered for award.
  > "The Offeror must respond to this RFP by submitting all data required in paragraph (B) below for its proposal to be evaluated and considered for award." ((2) Submission of All Data Required, p. 10 [S31.1])
- **R070** (mandatory) Failure to submit the required data is sufficient cause for disqualification of the proposal from further consideration.
  > "Failure to submit such data shall be deemed sufficient cause for disqualification of a proposal from further consideration." ((2) Submission of All Data Required, p. 10 [S31.1])
- **R071** (mandatory) The Offeror must submit its proposal on the basis that all proposals and their contents will be open to public inspection, without reservations.
  > "Therefore, the Offeror must submit its proposal based on such conditions without reservations." ((3) Public Inspection, p. 10 [S32.1])
- **R074** (mandatory) The proposal must include the Proposal Submission Form.
  > "The proposal submission form can be found here:" ((1) Proposal Submission Form, p. 10 [S35.1])
- **R075** (mandatory) The proposal must include a narrative-style description of how the Offeror will work with MoDOT to fulfill project-specific requirements.
  > "A narrative style description must be included of how the Offeror will work with MoDOT in order to fulfill project-specific requirements." ((2) Work Plan, p. 10 [S36.1])
- **R076** (mandatory) The Work Plan section must be no longer than ten (10) pages, excluding forms and resumes attached to the proposal. _(merged from R077)_
  > "This section should be no longer than ten (10) pages in length, with a font size no less than 12 points." ((2) Work Plan, p. 10 [S36.1])
- **R078** (mandatory) The project plan must include all items outlined in Section 2.
  > "The project plan shall include all items outlined in Section 2" ((2) Work Plan, p. 10 [S36.1])
- **R080** (mandatory) The proposal must indicate the name, location, telephone number, and email address of the Offeror's primary contact person.
  > "Please indicate the name, location, telephone number, and email address of the primary contact person for the Offeror." ((3) Personnel, pp. 10-11 [S37.1])
- **R081** (desired) The Personnel section of the proposal must highlight the Offeror's previous experience, including any relevant work with other state agencies or local governments in Missouri.
  > "Information presented in this section should highlight the previous Offeror experience, as well as any relevant work with other state agencies or local governments in Missouri." ((3) Personnel, pp. 10-11 [S37.1])
- **R082** (mandatory) The Offeror must furnish a complete listing of each Sub-Offeror, if any, together with complete contact information for that Sub-Offeror.
  > "The Offeror must furnish a complete listing of each Sub-Offeror, if any, and complete contact information for that Sub-Offeror." ((3) Personnel, pp. 10-11 [S37.1])
- **R083** (mandatory) The proposal must clearly identify the bidder's experience in offering the services requested in this RFP during the past three (3) years.
  > "The proposal must clearly identify the experience in offering the services requested in this RFP during the past three (3) years." ((4) Experience, p. 11 [S38.1])
- **R084** (desired) The experience description should include a list of the agencies the bidder's institution has served or currently serves.
  > "The description should include a list of the agencies which your institution has served or currently serves." ((4) Experience, p. 11 [S38.1])
- **R085** (desired) Proposals should indicate the name, title, and telephone number of at least three officials of clients within the past three years.
  > "Proposals should indicate the name, title, and telephone number of at least three officials of clients within the past three years." ((5) References, p. 11 [S39.1])
- **R086** (mandatory) Proposals must be submitted as one combined PDF document. _(merged from R087)_
  > "Proposals must be submitted as one combined PDF document." ((5) References, p. 11 [S39.1])
- **R088** (mandatory) The proposal must be organized in the following order: 1) Proposal Submission Form; 2) Cover Letter (Optional; 1 page maximum); 3) Body of Proposal (including work plan and project schedule); 4) Personnel; 5) Organization's Project Experience; 6) Team Member Experience; and 7) Organization's Client References.
  > "organized in the following order: 1) Proposal Submission Form; 2) Cover Letter (Optional; 1 page maximum); 3) Body of Proposal (including work plan and project schedule); 4) Personnel; 5) Organization's Project Experience; 6) Team Member Experience; and 7) Organization's Client References." ((5) References, p. 11 [S39.1])
- **R089** (mandatory) The optional cover letter must not exceed one page.
  > "Cover Letter (Optional; 1 page maximum)" ((5) References, p. 11 [S39.1])
- **R090** (mandatory) The Offeror bears sole responsibility for submitting all information related to the evaluation categories with its proposal, and MHTC's representative is not obligated to solicit any information that is missing from the proposal.
  > "it is the Offeror's sole responsibility to submit information related to the evaluation categories" ((3) Responsibility to Submit Information, p. 11 [S43.1])
- **R103** (mandatory) The Offeror's proposal must be submitted so that it is acceptable to MHTC without further clarification, since MHTC may accept it as-is.
  > "The Offeror is cautioned that its proposal shall be subject to acceptance by MHTC without further clarification." ((E) Components of Agreement, p. 13 [S53.1])
- **R106** (desired) Offerors are encouraged to submit copies of their existing affirmative action programs, if any.
  > "Offerors are encouraged to submit copies of their existing affirmative action programs, if any." ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])
- **R119** (mandatory) Each sole proprietor and general partner must submit a sworn affidavit of lawful presence using the form attached as Exhibit B. _(merged from R118)_
  > "A copy of the affidavit reference herein is provided within this document, attached as Exhibit B." ((L) Proof of Lawful Presence for Sole Proprietorships and Partnerships, p. 15 [S60.1])
- **R151** (mandatory) For a joint venture submission, a separate Annual Worker Eligibility Verification Affidavit must be provided for each business entity in the joint venture. _(merged from R152)_
  > "for joint ventures, a separate affidavit is required for each business entity" (EXHIBIT A: ANNUAL WORKER ELIGIBILITY VERIFICATION AFFIDAVIT, p. 19 [S74.1]; EXHIBIT B: APPLICANT AFFIDAVIT FOR SOLE-PROPRIETORSHIP OR PARTNERSHIP, p. 20 [S75.1])

### Other (4)

- **R079** (mandatory) The project plan must recognize MoDOT's ultimate authority to approve the work plans.
  > "recognize the ultimate authority of MoDOT to approve the work plans" ((2) Work Plan, p. 10 [S36.1])
- **R107** (desired) Offerors are encouraged to directly hire minorities and women as direct employees.
  > "Offerors are also encouraged to directly hire minorities and women as direct employees of the Offerors." ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])
- **R108** (desired) Offerors are encouraged to obtain MBE and WBE participation in this work through subcontractors, suppliers, joint ventures or other arrangements.
  > "Offerors are encouraged to obtain minority business enterprise (MBE) and women business enterprise (WBE) participation in this work through the use of subcontractors, suppliers, joint ventures, or other arrangements that afford meaningful participation for M/WBEs." ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])
- **R109** (desired) Offerors are encouraged to obtain 10% MBE and 5% WBE participation.
  > "Offerors are encouraged to obtain 10% MBE and 5% WBE participation." ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])

### Ambiguities

- **A01** The submission deadlines are not stated in this chunk; a bidder would ask for the exact due date and time (and time zone) for proposals. _(affects R005)_ (INTRODUCTION, p. 4 [S4.1])
- **A02** The fee proposal must be submitted on the "PRICE PAGE", but no price page is included in this text; the bidder would ask where the PRICE PAGE form is obtained and whether fees must be presented in a prescribed format or level of detail. _(affects R091)_ (PROPOSAL, p. 4 [S5.1])
- **A03** The text refers to "the MHTC parameters" as the basis for generating the draft LLD but never defines them; a bidder would ask what these parameters are and where they are documented. _(affects R014)_ ((B) Background, p. 5 [S9.1])
- **A04** The requirement to meet EPG Section 236.4.6.2 is stated without the section's content, so a bidder would ask whether that guide is provided or must be obtained, and which edition applies. _(affects R011)_ ((B) Background, p. 5 [S9.1])
- **A05** The table lists a 7/17/2024 4 p.m. (Central) deadline in the same row as the contact-method rule, but does not state what is due by that date (e.g., whether questions must be received by then). A bidder would ask whether 7/17/2024 is the deadline for submitting comments or questions. _(affects R017, R018)_ ((E) RFP Schedule, pp. 5-6 [S12.1])
- **A06** The schedule says MoDOT may expand the schedule without notification except for the proposal deadline date, but it is unclear whether the 8/21/2024 10 a.m. proposal deadline is the protected date or whether it too can move. A bidder would ask which dates are fixed. _(affects R001)_ ((E) RFP Schedule, pp. 5-6 [S12.1])
- **A07** The deliverables table lists items without dates, sequencing or acceptance criteria, so the bidder cannot tell when the draft and final report, the demonstration and the training are due relative to the project schedule. The bidder would ask for the milestone dates or the deliverable schedule. _(affects R023, R036, R038, R039)_ (Task Deliverables, p. 6 [S14.1])
- **A08** The scope of the required ROW staff training is undefined (number of sessions, audience size, format, location, and whether materials are included), which directly affects staffing and price. The bidder would ask for the expected training volume and delivery format. _(affects R036)_ (Task Deliverables, p. 6 [S14.1])
- **A09** The interim presentation must be "near the mid-point of the project", but the mid-point is undefined and the project duration is not stated in this text; the bidder would ask what date or project month the interim presentation is expected. _(affects R030)_ ((G) Project Schedule, pp. 6-7 [S15.1])
- **A10** The timeline presumes a November 1, 2024 start while the RFP is issued later, and the text says the timeline will be finalized during contracting; the bidder would ask whether the November 1, 2024 start date still applies and what the expected project duration is. _(affects R027, R028, R030)_ ((G) Project Schedule, pp. 6-7 [S15.1])
- **A11** The milestone table says the dates of key milestones and deliverables will be determined at the 11/15/2024 kick-off meeting, yet the table already fixes dates through 2/2/2026; a bidder would ask whether the listed dates are firm or subject to change at kick-off. _(affects R043, R034, R035, R036, R037, R038, R039, R040)_ ((G) Project Schedule, p. 7 [S15.2])
- **A12** The draft documents are said to be due 'approximately two months prior to the final report' while the table sets 11/3/2025 for drafts and 1/1/2026 for finals (about two months), and the final documents 'approximately one month before the end of the contract' while the contract ends 2/2/2026 (about one month); a bidder would ask which dates govern if the 'approximately' windows conflict with the fixed dates. _(affects R038, R039, R040)_ ((G) Project Schedule, p. 7 [S15.2])
- **A13** The services are defined only by reference to "the services listed below in (B)", which is not included in this chunk; the bidder would ask which task descriptions in (B) are binding obligations versus guidance, since the text says task descriptions are only intended to provide guidance. _(affects R041)_ ((A) Services, p. 8 [S17.1])
- **A14** It is unclear whether the $175,000 cap is an all-inclusive ceiling covering all tasks, or whether it applies only to a subset of the services; the bidder would ask what costs the cap must cover. _(affects R041)_ ((A) Services, p. 8 [S17.1])
- **A15** The chunk does not say what the "program proposal" must contain, what format the electronic copy must take, or when it is due; a bidder would ask for the required content, file format and submission deadline. _(affects R042)_ ((B) Specific Requirements, p. 8 [S18.1])
- **A16** The work plan is to detail implementation of "the following tasks", but this chunk does not enumerate them; the bidder would ask which tasks and deliverables the finalized work plan must cover. _(affects R046)_ (Task 1: Project Management, p. 8 [S19.1])
- **A17** The scope of the literature review is undefined: which states, time period, publication types and ROW use cases must be covered, and what depth or deliverable format constitutes a "thorough" review. The bidder would ask what coverage and output (report, matrix, presentation) the issuer expects. _(affects R050)_ (Task 2: Literature Review, p. 8 [S20.1])
- **A18** The text does not state what information about the program must accompany its name (version, license, hosting, security documentation) or the criteria MoDOT Information Systems will use to approve it, so the bidder cannot know what to submit or how long approval may take. _(affects R051, R052)_ (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1])
- **A19** The number and types of properties, and the format of the demonstration (live, recorded, sample outputs), are not specified, which affects effort and cost; the bidder would ask how many properties and what property types must be covered. _(affects R053)_ (Task 3c: Proof of Concept that AI/ML Can Develop Legal Land Descriptions, p. 9 [S23.1])
- **A20** The scope of the training is undefined: no format (in-person or virtual), duration, number of sessions, number of trainees, or location is given, so the bidder cannot size or price the training effort. The bidder would ask what training delivery format, duration and audience size are expected. _(affects R036, R055)_ (Task 4: Training and User Manual, p. 9 [S24.1])
- **A21** It is unclear whether the user manual must be delivered as a separate written document (and in what format, e.g. PDF or online help) or is simply a training handout, and whether it must be updated after delivery. The bidder would ask what deliverable format and level of detail the user manual requires. _(affects R055)_ (Task 4: Training and User Manual, p. 9 [S24.1])
- **A22** The scope of "all accompanying documentation identified as beneficial during the study" is open-ended and undefined, so the bidder cannot size the deliverable; the bidder would ask what documentation is expected and who determines what is beneficial. _(affects R056)_ (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **A23** The Publication Guidelines and summary template are referenced only as being "on the website" without a specific location or version, so the bidder would ask where to obtain them and which version governs. _(affects R063)_ (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **A24** The chunk does not state when the final report, research summary and presentation are due, nor whether the presentation is delivered in person or virtually; a bidder would ask for the delivery deadline and format. _(affects R056, R061, R062)_ (Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1])
- **A25** The text does not specify how often, in what form (meeting, written report) or on what triggers the Offeror must consult MHTC's representative, so the bidder cannot size the effort or price the ongoing administration support. _(affects R064)_ ((C) Administration of Program, p. 9 [S27.1])
- **A26** The submission deadline is stated only as "the due date indicated" without a date in this text, so a bidder cannot tell the actual due date from this chunk and would ask the issuer to confirm it. _(affects R001)_ ((1) Pricing and Signature, p. 10 [S30.1])
- **A27** The text says the section "should be no longer than ten (10) pages" while also stating the plan "shall include all items outlined in Section 2"; it is unclear whether the 10-page limit is a hard pass/fail constraint or a guideline, and whether the Section 2 items must fit within it. _(affects R076, R078)_ ((2) Work Plan, p. 10 [S36.1])
- **A28** The text requires "complete contact information" for each Sub-Offeror but does not say which fields that covers (unlike the primary contact, where name, location, phone and email are listed). A bidder would ask whether the same four fields suffice or whether additional details such as tax ID or registration numbers are needed. _(affects R082)_ ((3) Personnel, pp. 10-11 [S37.1])
- **A29** The references requirement asks for at least three client officials from the past three years but does not say whether these must be public-agency clients, whether they must be for similar legal-description or AI/ML work, or whether contact details must be verifiable/current; a bidder would ask what qualifies a reference. _(affects R085)_ ((5) References, p. 11 [S39.1])
- **A30** The text refers to "the evaluation categories" without listing them here, so a bidder cannot tell exactly what information must be submitted; the bidder would ask which evaluation categories and required content are meant. _(affects R090)_ ((3) Responsibility to Submit Information, p. 11 [S43.1])
- **A31** The text says a detailed budget will be developed later, so it is unclear how firm the submitted cost estimate must be and whether it becomes a binding price or is refined after award; the bidder would ask what level of detail and binding effect the cost estimate carries. _(affects R091, R092)_ ((1) Cost Estimate, p. 11 [S45.1])
- **A32** The cost estimate gives no period of performance or unit basis (e.g., per year, per task, total contract value), so a bidder cannot tell whether the amounts should cover one year, the full contract term, or a specific volume of work. The bidder would ask what period and pricing basis the Cost Estimate must cover. _(affects R091, R095)_ ((A) Cost Estimate, p. 12 [S47.1])
- **A33** The RFP refers to "the following contract provisions" but this chunk does not identify them; a bidder would ask which provisions apply and where they are set out, since they must be accepted as-is and disagreement can void the award. _(affects R097, R098)_ (SECTION (5): AGREEMENT REQUIREMENTS, p. 13 [S48.1])
- **A34** The text does not define what "fully coordinate" with the Construction and Materials Division requires (meeting cadence, review gates, approval of deliverables), which affects staffing and schedule; the bidder would ask what coordination activities and turnaround times are expected. _(affects R099)_ ((A) MHTC's Representative, p. 13 [S49.1])
- **A35** The text says the proposal must be acceptable without further clarification, yet MHTC reserves the right to clarify relationships in writing and have that clarification govern. A bidder would ask whether post-submission clarifications can change scope, price or terms after the proposal is accepted. _(affects R103, R104)_ ((E) Components of Agreement, p. 13 [S53.1])
- **A36** The 10% MBE / 5% WBE participation is only "encouraged" and it is unclear whether these percentages are evaluated, reported, or contractually committed; the bidder would ask whether the goals must be met and documented in the proposal. _(affects R109)_ ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])
- **A37** The text does not state what Section (3), paragraph I contains, so the bidder cannot tell which obligations must be flowed down to subcontractors; the bidder would ask for the text of Section (3), paragraph I. _(affects R113)_ ((J) Incorporation of Provisions, p. 14 [S58.1])
- **A38** The scope of the Commission's direction over subcontracts and the sanctions for noncompliance are undefined, so the bidder cannot assess subcontractor risk or cost; the bidder would ask what actions and sanctions may be directed. _(affects R114)_ ((J) Incorporation of Provisions, p. 14 [S58.1])
- **A39** The text does not define what counts as "confidential factual matters" or how such material will be marked or identified, so the bidder cannot tell what handling, storage or personnel restrictions it must price; the bidder would ask MHTC for a definition and marking convention. _(affects R121, R122)_ ((R) Confidentiality, p. 16 [S66.1])
- **A40** "Immediately" sets no measurable notification deadline (e.g., hours) and no channel or contact for the notice, so the bidder cannot design a compliant escalation process; the bidder would ask what timeframe and method MHTC requires. _(affects R122)_ ((R) Confidentiality, p. 16 [S66.1])
- **A41** The clause grants MHTC rights to reproduce and use "any products derived from the Offeror's work" without royalties, but does not state who owns the deliverables or whether pre-existing Offeror IP/tools are included; a bidder would ask what ownership and license rights it retains in its models, code and data. _(affects R125)_ ((U) Maintain Papers, p. 16 [S69.1])
- **A42** The insurance coverages are framed as something the Offeror "may be asked" to provide and that must "meet, or approach" the listed amounts, so it is unclear whether these limits are binding contract requirements or merely indicative; the bidder would ask whether certificates at exactly these limits are required and whether they must be submitted with the proposal or only before contract signing. _(affects R126, R127, R128, R129)_ ((X) Insurance, p. 17 [S72.1])
- **A43** The text refers to an "Approved Technologies section of this document" that is not included in this chunk, so a bidder cannot tell whether the list here is exhaustive or whether additional approved technologies exist; the bidder would ask which technologies are formally approved. _(affects R130)_ ((Y) Information Technology, pp. 17-18 [S73.1])
- **A44** The threshold for "large scale use of Python" is undefined, so a bidder cannot tell whether its intended use requires BRPT approval and the associated schedule risk; the bidder would ask what volume or scope triggers the approval requirement. _(affects R137)_ ((Y) Information Technology, pp. 17-18 [S73.1])
- **A45** The database platform requirement is internally inconsistent: Oracle 19C is stated as mandatory while SQL Server is presented as an alternative, and it is unclear whether the vendor may choose either platform or whether Oracle 19C is required unless an exception is approved. The bidder would ask which database platform is required and who approves an alternative. _(affects R143, R144)_ ((Y) Information Technology, p. 18 [S73.2])
- **A46** The text does not define what constitutes a 'specific business need' for storing PII or the process and timeline for obtaining IS Cyber Security Team approval, which affects design and schedule. The bidder would ask for the approval criteria and process. _(affects R145, R146)_ ((Y) Information Technology, p. 18 [S73.2])
- **A47** Conflicting requirements R034 and R047: R034 fixes the data management plan due date as 12/4/2024, while R047 requires it within 2 weeks after the kick-off meeting (11/15/2024), i.e., by about 11/29/2024. _(affects R034, R047)_ ((G) Project Schedule, p. 7 [S15.2]; Task 1: Project Management, p. 8 [S19.1])
- **A48** Conflicting requirements R030 and R037: R030 requires the interim presentation near the project mid-point, whereas R037 fixes it by 9/15/2025, roughly ten months into the 15-month contract. _(affects R030, R037)_ ((G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])
- **A49** Conflicting requirements R143 and R144: R143 mandates Oracle 19C for on-premise database deployments while R144 contemplates Microsoft SQL Server as the database platform. _(affects R143, R144)_ ((Y) Information Technology, p. 18 [S73.2])

### Gaps

- **G01** An attachment is referenced but not included in this chunk; the bidder needs it to know what forms or requirements accompany the proposal. _(referenced document: Attachment)_ (Front matter, pp. 1-2 [S1.1])
- **G02** The letter points to a web page for more information about project contracting in general, which may hold additional requirements or forms. _(referenced document: https://www.modot.org/information-researchers)_ (Front matter, pp. 1-2 [S1.1]; (1) Cost Estimate, p. 11 [S45.1])
- **G03** The PRICE PAGE form on which the fee proposal must be submitted is referenced but not provided in this chunk. _(referenced document: PRICE PAGE)_ (PROPOSAL, p. 4 [S5.1])
- **G04** The MoDOT Engineering Policy Guide (EPG) Section 236.4.6.2, which defines the requirements property descriptions must meet, is referenced but not included in this text. _(referenced document: MoDOT Engineering Policy Guide (EPG) Section 236.4.6.2)_ ((B) Background, p. 5 [S9.1])
- **G05** The Standard Research Agreement, which the bidder must review for contractual terms, is provided separately on the issuer's website. _(referenced document: Standard Research Agreement)_ ((D) Contract Period and Budget, p. 5 [S11.1])
- **G06** The Publication Guidelines document referenced for report formatting is not included in this chunk. _(referenced document: Publication Guidelines)_ (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **G07** The summary template referenced for the Research Summary is provided separately on the website. _(referenced document: summary template)_ (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **G08** The Publications Guidelines governing the format of the final report and research summary are published on a website and not included in the RFP text. _(referenced document: Publications Guidelines)_ (Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1])
- **G09** The Proposal Submission Form itself is not included in the RFP; the bidder must obtain it from the MoDOT information-for-researchers web page. _(referenced document: Proposal Submission Form)_ ((1) Proposal Submission Form, p. 10 [S35.1])
- **G10** Executive Order 07-13 is incorporated by reference but its full text is not reproduced in this RFP, so the bidder must obtain it to confirm the compliance obligations it imposes. _(referenced document: Executive Order 07-13)_ ((I) Executive Order, p. 14 [S57.1])
- **G11** The sworn affidavit the bidder must submit is provided as an attachment to the RFP but is not included in this chunk. _(referenced document: Exhibit A)_ ((K) Non-employment of Unauthorized Aliens, pp. 14-15 [S59.1])
- **G12** The sworn affidavit of lawful presence that sole proprietors and general partners must submit is provided as a separate exhibit, which the bidder needs to complete and submit. _(referenced document: Exhibit B)_ ((L) Proof of Lawful Presence for Sole Proprietorships and Partnerships, p. 15 [S60.1])
- **G13** The State of Missouri Accessibility Standard that web applications must meet is referenced as an external document/web page rather than reproduced in the RFP. _(referenced document: State of Missouri's Accessibility Standard)_ ((Y) Information Technology, p. 18 [S73.2])
- **G14** The affidavit form itself is referenced by title but its content, fields and signature requirements are not included in this text; the bidder needs the actual form to complete it. _(referenced document: ANNUAL WORKER ELIGIBILITY VERIFICATION AFFIDAVIT)_ (EXHIBIT A: ANNUAL WORKER ELIGIBILITY VERIFICATION AFFIDAVIT, p. 19 [S74.1])

## Proposed solution

The bid is a 15-month research and proof-of-concept engagement for MHTC/MoDOT, run by MoDOT's Research Unit, that determines whether AI/ML can produce a usable first draft of a legal land description (LLD) for Right of Way staff to review and edit. We deliver a literature review of other state DOTs' AI/ML use in right of way, a named and IS-approved LLD generation program, a demonstration of draft LLDs across a variety of property types, a trained ROW user base with a user manual, and the draft and final reports, research summary and staff presentation. The shape is mostly build-and-configure on a small, MoDOT-compliant web application plus research and advisory work; nothing is procured on MoDOT's behalf and no licensing burden is placed on MoDOT. Delivery runs in four phases: mobilisation and planning (kick-off, work plan, Data Management Plan, program naming and IS approval), research and baseline (literature review, EPG 236.4.6.2 and MHTC parameter capture), build and demonstrate (iterative LLD generation with MoDOT feedback, 4/25/2025 demonstration), then training, reporting and close-out (manual and training by 7/25/2025, interim presentation 9/15/2025, drafts 11/3/2025, finals 1/1/2026, final invoice 2/2/2026). The team is a principal investigator-led research group with a land-surveying/ROW subject-matter expert, an AI/ML engineer, a .NET web developer, a technical writer/trainer and a contract-compliance lead, all coordinated with the Construction and Materials Division. Everything is priced inside the $175,000 not-to-exceed cap on the Section (4) Price Page line items, and the bid is filed and every question channelled through MoDOTResearchRFP@modot.mo.gov by the RFP's stated deadlines.

### Coverage

Covers 75 of 75 mandatory requirements.

### Components

#### C01. Bid administration, submission and clarification discipline

We run the proposal itself as a controlled deliverable: the combined PDF is filed to MoDOTResearchRFP@modot.mo.gov before the RFP's stated proposal deadline, and we treat time as of the essence, holding internal sign-off and file-assembly dates ahead of the deadline so no late or partial filing is possible. Every question or comment on the RFP is sent only to MoDOTResearchRFP@modot.mo.gov by the date and time listed in Section 1E, and no member of the bid team contacts MoDOT employees by any other method, since doing so is cause for disqualification. We log each question, the date sent and MoDOT's posted response, and we build the proposal on the assumption that MoDOT's written responses and clarifications govern. This component also carries the post-award close-out discipline: the final invoice is submitted and the contract closed on 2/2/2026, with all billing completed against the 1/1/2026 final deliverables so nothing is left outstanding at contract end.

Addresses: R005, R040, R073.

- Proposals are due by 10 a.m. Central on August 21, 2024 to MoDOTResearchRFP@modot.mo.gov, with receipt acknowledged by noon the same day. ((E) RFP Schedule, pp. 5-6 [S12.1]; (1) Pricing and Signature, p. 10 [S30.1])
- All questions and comments must go only to MoDOTResearchRFP@modot.mo.gov by 4 p.m. Central on July 17, 2024. ((E) RFP Schedule, pp. 5-6 [S12.1]; (4) Clarification of Requirements, p. 10 [S33.1])
- The final invoice is due and the contract ends on 2/2/2026. ((G) Project Schedule, p. 7 [S15.2])

#### C02. Mobilisation, work plan and governance

We facilitate the kick-off meeting with MoDOT on 11/15/2024 to review the work plan, scope and schedule and to agree a protocol for regular communication and coordination with the Research Unit and Construction and Materials Division. We finalise a work plan that details implementation of every project task together with the resources and schedule needed to carry them out, and that expressly recognises MoDOT's ultimate authority to approve work plans. The plan is built to the 15-month contract period and to the fixed milestone calendar, and we consult MHTC's designated representative (MoDOT Research Director Jen Harper or her delegate) on any concern about administration of the services, with a standing monthly check-in for that purpose. We fully coordinate our activities with the Construction and Materials Division and keep advice and information on matters covered by the Agreement available to that Division throughout the term.

Addresses: R010, R015, R043, R046, R079, R099, R100, R064.

- MoDOT's Research Director, Jen Harper, is MHTC's designated representative for administering the agreement and may delegate authority. ((A) MHTC's Representative, p. 13 [S49.1]; Front matter, pp. 1-2 [S1.1])
- The contract period is 15 months, estimated to start 11/1/2024 and end 2/2/2026. ((D) Contract Period and Budget, p. 5 [S11.1]; (G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])

#### C03. Reporting, meetings and schedule control

We run a single reporting calendar that satisfies every cadence the RFP sets: monthly e-mail and phone updates to MoDOT contacts on progress, quarterly written updates on work accomplished submitted on or before the last working day of March, June, September and December, and quarterly status meetings (in person or online) reviewing the previous period and the anticipated next period. We produce written minutes for the kick-off meeting and for every quarterly status meeting and circulate them for MoDOT confirmation. We schedule the interim presentation near the project mid-point, and no later than 9/15/2025, to update MoDOT on progress and project direction. All meetings and events are scheduled between 7:30 a.m. and 4 p.m. Central time, and the schedule is tracked against the fixed milestone dates with early warning to MoDOT of any slippage.

Addresses: R016, R028, R030, R031, R037, R044, R045.

- MoDOT's fiscal year runs July 1 to June 30, which drives the quarterly reporting cycle submitted to FHWA. ((C) Fiscal Year, p. 5 [S10.1]; (G) Project Schedule, pp. 6-7 [S15.1])

#### C04. Data Management Plan and data handling

We deliver a Data Management Plan to MoDOT within two weeks of the kick-off meeting, and in any event by the 12/4/2024 milestone, describing the anticipated formats of our data and related files. The DMP commits us to platform-independent, non-proprietary formats (for example plain-text/CSV, GeoJSON and PDF/A) so the data retains maximum future utility for MoDOT, and it sets out storage, versioning, retention and hand-back of the working papers and records we must maintain. It also records our PII position: no personally identifiable information is stored in any database table without a specific business need, and any PII that is stored is submitted for IS Cyber Security Team approval before the table is created.

Addresses: R034, R047, R048, R049, R123, R145, R146.

- The Data Management Plan is due within two weeks after the kick-off meeting, and the milestone table fixes 12/4/2024. (Task 1: Project Management, p. 8 [S19.1]; (G) Project Schedule, p. 7 [S15.2])

#### C05. Literature review of state DOT AI/ML practice

We conduct a thorough literature search and review of other state DOT practices using AI/ML for right-of-way purposes, covering published research, DOT technical reports, peer-exchange material and vendor case studies, and we deliver it as a structured report with a comparison matrix of use cases, methods, results and lessons learned. The review is scoped with MoDOT at kick-off so that the states, period and ROW use cases covered match what the Research Unit and Right of Way staff need, and its findings feed directly into the design of the LLD generation approach and the final report.

Addresses: R050.

#### C06. LLD generation program: naming, IS approval and compliance

Before any proof-of-concept work begins we name the program we will use to develop the LLDs and submit it, with version, licensing, hosting and security information, for MoDOT Information Systems approval; no Task 3c work starts until that approval is in hand. The application is built on a currently supported .NET 6.0 or above release (falling back to .NET Framework 4.8 or above only if a specific need is shown), using MVC, Razor Pages or Web API, and written in the approved languages C#, JavaScript, CSS, HTML and Python, with Python confined to ESRI scripts and small one-time uses unless the IS Best Practices Review Team approves larger use. It is a web-based browser application requiring no client-side software beyond a modern browser (no Java Applets, no Silverlight), tested against the latest IS-approved browsers, and it meets the State of Missouri Accessibility Standard (Section 508 as amended and WCAG) including WCAG 2.1 AA. It runs on Oracle 19C for on-premise deployment, with any SQL Server option used only where MoDOT IS Data Service Management approves it, and library dependencies are reviewed and updated annually. We use no third-party tool or software that places a licensing responsibility on MoDOT without prior review and approval by the IS Best Practices Review Team and IS management, and we use no text, diagrams, photographs, audio, multimedia, source code, scripts or graphics from another author's web pages unless the author permits free copying or arrangements are made with the author. Vendor logos and branding are suppressed wherever a supported, licensed option exists to remove them.

Addresses: R052, R130, R131, R132, R133, R134, R135, R136, R137, R138, R139, R140, R142, R143, R144, R147, R149, R150.

- MoDOT Information Systems must approve the named LLD development program before Task 3c can proceed. (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1])

#### C07. EPG-compliant LLD drafting engine and MHTC parameter capture

We build the drafting engine that turns MHTC parameters into a first-draft legal land description for MoDOT Right of Way staff to review and edit. The engine encodes the drafting rules the RFP requires: descriptions are produced in metes and bounds form, and where a property is acquired in its entirety the description is reproduced exactly as it appears on the last deed of record for that property. Output is generated to meet MoDOT Engineering Policy Guide Section 236.4.6.2, and every draft is routed for professional land surveyor review against the right of way plans before any deed is presented to a grantor. We capture the MHTC parameters and the EPG rules in a documented parameter and rules specification agreed with MoDOT at kick-off, so the drafting logic is auditable and can be tuned as feedback arrives.

Addresses: R011, R012, R013, R014.

- Descriptions prepared for MHTC must meet EPG Section 236.4.6.2 and be reviewed by a professional land surveyor against the right of way plans before a deed is presented to the grantor. ((B) Background, p. 5 [S9.1])

#### C08. Proof of concept, demonstration and feedback loop

We run the proof of concept on a set of MoDOT-supplied example LLDs and a variety of property types agreed at kick-off, generating draft LLDs and capturing MoDOT's review comments as structured improvement feedback. On 4/25/2025 we present how the AI/ML creates draft LLDs and how MoDOT feedback is incorporated for improvement, demonstrating the AI writing a legal land description live against the agreed property set. We then adjust the tool on the basis of that feedback before training, and we demonstrate draft LLD generation across the variety of properties required, with each round's outputs and changes recorded so MoDOT can see the improvement trajectory.

Addresses: R023, R035, R053.

- MoDOT supplies example LLDs on 12/20/2024 for the proof of concept. ((G) Project Schedule, p. 7 [S15.2])

#### C09. Training, user manual and ROW staff enablement

After the tool adjustments, and by 7/25/2025, we deliver a written user manual and train MoDOT Right of Way staff on the tool. The manual is a standalone reference document covering the parameter inputs, how to run a draft, how to review and edit the output, and the surveyor review step, delivered in an accessible, platform-independent format and updated once more before the final submission. Training is delivered in sessions sized and formatted to the audience MoDOT confirms at kick-off, with recorded sessions and the manual left with MoDOT so new staff can be onboarded after the contract ends.

Addresses: R036, R055.

#### C10. Reports, research summary and staff presentation

We prepare the draft Synthesis Report and Research Summary with all accompanying documentation identified as beneficial during the study, due 11/3/2025, and the final report, research summary, presentation and user manual due 1/1/2026, roughly a month before contract end so all billing can be completed. The research summary is a 1-2 page statement of project objectives, findings and conclusions, and the presentation summarises the significant details of the project for MoDOT staff. Reports follow the MoDOT Publication Guidelines and the research summary template, and the final report carries a completed Technical Report Documentation page.

Addresses: R038, R039, R056, R061, R062.

- The draft final report, summary report and user manual are due 11/3/2025 and the final versions 1/1/2026, with the contract ending 2/2/2026. ((G) Project Schedule, p. 7 [S15.2])

#### C11. Pricing, contract and compliance obligations

We price the whole scope of work at a total not to exceed $175,000 and submit a proposed cost estimate covering all services in the Scope of Work on Section (4), the Price Page, broken out into Salaries, Benefits, Operating Expense, Facilities and Administration (F&A) Cost, Miscellaneous and Total, with Miscellaneous costs itemised on an additional sheet where needed; we agree to provide the services at the fees quoted under the terms of the RFP. We accept that the award incorporates the contract provisions specified in the RFP and is subject to a post-award negotiated contract, and that MHTC may cancel the award and select another Offeror if terms cannot be agreed; we accept that written clarifications issued by MHTC govern over conflicting requirements, and that any change to the Agreement requires a formal amendment signed by both authorised representatives. We will not release any material or report to the public without MHTC's representative's prior consent, will not assign, delegate or novate any interest without prior written consent, and will not disclose confidential factual matters supplied by MHTC except as required by statute, ordinance or court order or as authorised by MHTC's representative, notifying MHTC immediately of any such request. All documents, reports, exhibits and deliverables we produce at MHTC's direction, and all information MHTC supplies, remain MHTC property, and we maintain all working papers and records and make them available at no charge to MHTC and the Missouri State Auditor at all reasonable times during the term and for three years from final payment. We remain ultimately responsible and liable to MHTC for the complete, accurate and professional quality and performance of the services regardless of any subcontractor or supplier, and we flow the Section (3) paragraph I provisions into every subcontract and take such action with respect to any subcontract as the Commission may direct, including sanctions for noncompliance. We comply with Missouri Executive Order 07-13, certify by signature that every employee assigned is eligible and authorised to work in the United States, submit the Exhibit A sworn affidavit of E-Verify enrolment and no unauthorised alien employment, and submit the Exhibit B affidavit of lawful presence where the Offeror is a sole proprietorship or partnership. We will provide General Liability and Automobile Liability insurance of at least $500,000 per person and $3,000,000 per occurrence and a Missouri workers' compensation policy, and can evidence certificates before signing. We pursue 10% MBE and 5% WBE participation through subcontracting and direct hiring of minorities and women, while remaining fully liable for subcontractor performance.

Addresses: R007, R041, R091, R092, R095, R096, R097, R098, R101, R102, R104, R105, R107, R108, R109, R110, R111, R112, R113, R114, R116, R117, R120, R121, R122, R124, R125, R126, R127, R128, R129.

- Services are capped at a not-to-exceed amount of $175,000. ((A) Services, p. 8 [S17.1])
- Offerors may be asked before signing to provide insurance of at least $500,000 per person and $3,000,000 per occurrence plus Missouri workers' compensation. ((X) Insurance, p. 17 [S72.1])

### Assumptions

- The 8/21/2024 10 a.m. Central proposal deadline is treated as fixed and protected, and the November 1, 2024 start with the milestone dates through 2/2/2026 is treated as the baseline schedule, with any re-baselining at the 11/15/2024 kick-off limited to internal task sequencing rather than the fixed deliverable dates. *(inference)* ((E) RFP Schedule, pp. 5-6 [S12.1]; (G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])
- The 7/17/2024 4 p.m. Central date is treated as the deadline for submitting questions and comments on the RFP, and no question is raised after it. *(inference)* ((E) RFP Schedule, pp. 5-6 [S12.1]; (4) Clarification of Requirements, p. 10 [S33.1])
- The Data Management Plan is delivered by the earlier of the two stated dates, i.e. within two weeks of the 11/15/2024 kick-off, which also satisfies the 12/4/2024 milestone. *(inference)* ((G) Project Schedule, p. 7 [S15.2]; Task 1: Project Management, p. 8 [S19.1])
- The interim presentation is scheduled at the project mid-point and in any event no later than 9/15/2025, so the 9/15/2025 date governs if the two conflict. *(inference)* ((G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])
- The $175,000 cap is an all-inclusive ceiling covering every task in the Scope of Work, including training, reporting and travel, and the cost estimate is priced for the full 15-month term rather than per year. *(inference)* ((A) Services, p. 8 [S17.1]; (A) Cost Estimate, p. 12 [S47.1])
- The MHTC parameters and the content of EPG Section 236.4.6.2 are assumed to be obtainable from MoDOT at kick-off and captured in a written parameter and rules specification agreed with the Research Unit before build begins. *(inference)* ((B) Background, p. 5 [S9.1])
- The proof of concept is assumed to cover a modest set of property types (roughly 10-20 example properties) drawn from the MoDOT-supplied example LLDs, with the demonstration delivered live with recorded backup. *(inference)* (Task 3c: Proof of Concept that AI/ML Can Develop Legal Land Descriptions, p. 9 [S23.1]; Task Deliverables, p. 6 [S14.1])
- Training is assumed to be delivered as a small number of virtual or on-site sessions for the MoDOT Right of Way review group, with a standalone PDF user manual, sized within the fixed price rather than priced per trainee. *(inference)* (Task 4: Training and User Manual, p. 9 [S24.1]; Task Deliverables, p. 6 [S14.1])
- The literature review is assumed to be delivered as a written report with a comparison matrix covering other state DOTs' AI/ML right-of-way uses over roughly the last decade, since the RFP sets no narrower scope. *(inference)* (Task 2: Literature Review, p. 8 [S20.1])
- The LLD generation program is assumed to be a MoDOT-hosted web application on Oracle 19C built in .NET 6.0 or above, with no third-party component that creates a licensing obligation for MoDOT, so no BRPT licensing review is triggered. *(inference)* ((Y) Information Technology, pp. 17-18 [S73.1]; (Y) Information Technology, p. 18 [S73.2])
- The insurance limits are treated as binding contract requirements to be evidenced by certificate before signing rather than with the proposal. *(inference)* ((X) Insurance, p. 17 [S72.1])
- The 10% MBE and 5% WBE goals are treated as aspirational participation targets we will document and report, not as a pass/fail condition of the proposal. *(inference)* ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])
- The Publication Guidelines, research summary template, Price Page, Proposal Submission Form and Standard Research Agreement are assumed to be the versions currently posted at https://www.modot.org/information-researchers and are incorporated as the governing formats. *(inference)* ((D) Contract Period and Budget, p. 5 [S11.1]; Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1]; Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1]; (1) Proposal Submission Form, p. 10 [S35.1]; (1) Cost Estimate, p. 11 [S45.1])
- The Section (3) paragraph I subcontract provisions and the Executive Order 07-13 obligations are assumed to be the standard MoDOT flow-down terms, which we accept and pass through to subcontractors without negotiation. *(inference)* ((J) Incorporation of Provisions, p. 14 [S58.1]; (I) Executive Order, p. 14 [S57.1])
- Confidential factual matters are assumed to be marked as confidential by MHTC at the time of supply, with notification of any third-party request made to MHTC's representative within one business day. *(inference)* ((R) Confidentiality, p. 16 [S66.1])

## Risks

| ID | Risk | Severity | Likelihood | Source |
|---|---|---|---|---|
| K01 | IS approval of the named LLD program gates the whole build | high | medium | RFP |
| K02 | EPG 236.4.6.2 and the MHTC parameters are not in the RFP | high | medium | RFP |
| K03 | The $175,000 cap may not cover the full scope as the bidder reads it | high | medium | RFP |
| K04 | Oracle 19C vs SQL Server conflict leaves the hosting design and price unsettled | medium | high | RFP |
| K05 | Exhibits A and B are referenced but not in the RFP | medium | high | RFP |
| K06 | Python use may need BRPT approval before the proof of concept | medium | medium | Solution |
| K07 | Unreadable pages 19 and 20 may hide binding requirements | medium | medium | RFP |
| K08 | Training and user manual scope is undefined inside a fixed price | medium | medium | Solution |
| K09 | Proof-of-concept property set is not defined, so demonstration effort is unpriced | medium | medium | Solution |
| K10 | Referenced forms and guidelines are outside the RFP and may change the submission | medium | medium | RFP |
| K11 | Data Management Plan due date conflicts with the kick-off-relative deadline | low | medium | RFP |
| K12 | Interim presentation date conflicts with the mid-point requirement | low | medium | RFP |

### K01. IS approval of the named LLD program gates the whole build

No Task 3c work may start until MoDOT Information Systems approves the named LLD development program, and the RFP does not say what must accompany the name or what criteria or turnaround the approval uses. If approval is slow or refused, the build, the 4/25/2025 demonstration and everything downstream compress into a shorter window, and the bidder absorbs the idle effort within the fixed price.

**Why:** The gate is mandatory and sits before the build phase, but the RFP gives no approval criteria or timeline, so the delay depends on facts the RFP does not settle. (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1])

**Mitigation:** Ask MoDOT IS for the approval checklist and expected turnaround before the deadline; submit the program name and full technical package immediately after kick-off and hold a pre-approved fallback program in reserve.

**Related requirements:** R051, R052.

### K02. EPG 236.4.6.2 and the MHTC parameters are not in the RFP

The drafting engine must meet MoDOT Engineering Policy Guide Section 236.4.6.2 and generate drafts from 'the MHTC parameters', but neither the guide nor a definition of the parameters is provided. The bidder is therefore pricing an engine against rules it has not read; if the guide turns out to be detailed or the parameters numerous, the rules specification and the engine need unplanned work.

**Why:** The core technical requirement rests on two documents the RFP does not supply, and the solution assumes both are obtainable at kick-off and captured before build begins. ((B) Background, p. 5 [S9.1])

**Mitigation:** Ask for EPG 236.4.6.2 and the MHTC parameter list with the RFP response; state in the proposal that the price assumes the current published edition and a bounded parameter set, with scope beyond that handled as a change order.

**Related requirements:** R011, R012, R013, R014.

### K03. The $175,000 cap may not cover the full scope as the bidder reads it

The RFP caps the work at $175,000 but does not say whether the cap is all-inclusive across every task, and the task descriptions are described as guidance only. The solution prices the entire fifteen-month scope, including training, reporting and travel, inside the cap; if the true scope is larger than the bidder's reading, the engagement runs at a loss, and if the cap covers only part of the work the price page may be structured wrongly.

**Why:** A fixed ceiling against an ambiguously bounded scope is the single largest commercial exposure, and the solution's all-inclusive reading is an explicit assumption rather than a stated RFP fact. ((A) Services, p. 8 [S17.1]; (A) Cost Estimate, p. 12 [S47.1])

**Mitigation:** Ask MoDOT before the deadline whether the cap is all-inclusive and which task descriptions are binding; state in the proposal that the price covers the full scope as described and that additional tasks would require a formal amendment.

**Related requirements:** R041, R091, R092, R095, R096.

### K04. Oracle 19C vs SQL Server conflict leaves the hosting design and price unsettled

The RFP requires on-premise deployments to run on Oracle 19C while also requiring the application to be designed and maintained on the latest supported Microsoft SQL Server, with SQL Server 2016+ only by MoDOT IS Data Service Management approval. The proposed solution commits to Oracle 19C and treats SQL Server as an exception path, so if MoDOT's IS team expects SQL Server (or an approved exception is refused), the data layer, hosting and testing are rebuilt after award. Either way the bidder carries the rework inside a fixed $175,000 ceiling.

**Why:** The two requirements are directly contradictory and the RFP does not say who chooses the platform; the solution resolves the conflict by assumption rather than by a written clarification. ((Y) Information Technology, p. 18 [S73.2])

**Mitigation:** Submit a written question before the 7/17/2024 deadline asking which platform governs and who approves an alternative; state in the proposal that Oracle 19C is the priced baseline and that a SQL Server variant would be a change order.

**Related requirements:** R143, R144.

### K05. Exhibits A and B are referenced but not in the RFP

The RFP requires an Exhibit A sworn affidavit of E-Verify enrolment and no unauthorised alien employment, and an Exhibit B affidavit of lawful presence for sole proprietors and partnerships, but neither exhibit is included in the document. The bidder cannot confirm the exact wording, notarisation or signature requirements, and a defective or missing affidavit is a submission defect that can disqualify the proposal.

**Why:** Both exhibits are named as mandatory submission items and both are absent from the RFP, so the bidder must reconstruct them from the MoDOT web page before the 8/21/2024 deadline.

**Mitigation:** Download the current Exhibit A and Exhibit B forms from the MoDOT information-for-researchers page at once, confirm with MoDOTResearchRFP@modot.mo.gov that they are the governing versions, and have the affidavits executed and notarised well before the filing date.

**Related requirements:** R116, R117, R119, R151.

### K06. Python use may need BRPT approval before the proof of concept

The RFP confines Python to ESRI scripts and small one-time uses and requires IS Best Practices Review Team approval for larger use, without defining the threshold. AI/ML work in practice leans heavily on Python, so if the LLD engine needs more Python than the RFP contemplates, the bidder must either re-engineer in C# or wait on a BRPT review that could delay the 4/25/2025 demonstration.

**Why:** The solution assumes Python stays small and no BRPT review is triggered, but the threshold is undefined and the AI/ML component is the core of the work. ((Y) Information Technology, pp. 17-18 [S73.1])

**Mitigation:** State in the proposal that the LLD engine is written in C# with Python limited to ESRI scripts, and ask MoDOT IS to confirm the volume that triggers BRPT review so the design is fixed before build.

**Related requirements:** R137, R136, R130.

### K07. Unreadable pages 19 and 20 may hide binding requirements

Pages 19 and 20 carry almost no extractable text and are dominated by images, so whatever they contain — likely the task list, milestone table or deliverable detail — has not been read. If those pages set obligations the bidder has not priced, the proposal may be non-responsive or the work under-priced.

**Why:** Two consecutive pages of the RFP could not be parsed and they sit in the section that appears to carry the task and milestone detail the solution relies on.

**Mitigation:** Obtain a readable copy of pages 19 and 20 from MoDOT before the question deadline, re-check the work plan and price against them, and flag any newly found obligation in the proposal.

**Related requirements:** R046, R078.

### K08. Training and user manual scope is undefined inside a fixed price

The RFP requires training and a user manual for Right of Way staff by 7/25/2025 but gives no audience size, number of sessions, format or location, and the solution assumes a small number of virtual or on-site sessions priced within the cap. If MoDOT expects repeated on-site training across districts, the effort and travel cost grow with no price relief.

**Why:** Training is a mandatory deliverable with an open-ended scope, and the solution's sizing rests on an explicit assumption rather than on anything the RFP states. (Task 4: Training and User Manual, p. 9 [S24.1]; Task Deliverables, p. 6 [S14.1])

**Mitigation:** State the assumed training volume in the proposal (for example two sessions for up to fifteen ROW staff, virtual or at MoDOT premises) and ask MoDOT before the deadline to confirm the expected audience and format.

**Related requirements:** R036, R055.

### K09. Proof-of-concept property set is not defined, so demonstration effort is unpriced

The RFP requires a demonstration of draft LLDs across 'a variety of properties' and a live demonstration on 4/25/2025, but does not say how many properties or which types. The solution assumes roughly 10-20 example properties; a larger or more complex set, or example LLDs delivered late on 12/20/2024, would compress the build and demonstration window.

**Why:** The demonstration is a fixed-date mandatory deliverable whose effort depends on a property count the RFP does not give, and the example LLDs arrive only four months before the demonstration. (Task 3c: Proof of Concept that AI/ML Can Develop Legal Land Descriptions, p. 9 [S23.1]; Task Deliverables, p. 6 [S14.1]; (G) Project Schedule, p. 7 [S15.2])

**Mitigation:** State the assumed property count and types in the proposal, ask MoDOT to confirm the demonstration set at kick-off, and prepare a recorded backup demonstration in case live generation fails.

**Related requirements:** R023, R053, R035.

### K10. Referenced forms and guidelines are outside the RFP and may change the submission

The Price Page, Proposal Submission Form, Standard Research Agreement, Publication Guidelines and research summary template are all referenced but not included, and the solution assumes the versions currently posted on the MoDOT website govern. If those documents impose formatting, pricing or contractual terms the bidder has not seen, the proposal may be non-responsive or the post-award contract may carry obligations not priced.

**Why:** Five governing documents sit outside the RFP and the solution relies on an assumption about which versions apply; the Standard Research Agreement in particular is a post-award contract the bidder has not reviewed. ((D) Contract Period and Budget, p. 5 [S11.1]; Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1]; Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1]; (1) Proposal Submission Form, p. 10 [S35.1]; (1) Cost Estimate, p. 11 [S45.1])

**Mitigation:** Download every referenced document from the MoDOT information-for-researchers page before drafting, confirm the versions with MoDOTResearchRFP@modot.mo.gov, and review the Standard Research Agreement for terms that need a price or a stated exception.

**Related requirements:** R074, R063, R097, R098, R092.

### K11. Data Management Plan due date conflicts with the kick-off-relative deadline

One requirement fixes the Data Management Plan at 12/4/2024 while another requires it within two weeks of the 11/15/2024 kick-off, roughly 11/29/2024. The solution plans to the earlier date, which is safe, but if MoDOT treats 12/4/2024 as the contractual milestone and the kick-off slips, the two dates diverge and the bidder risks a missed milestone or a disputed deliverable.

**Why:** The conflict is real but the solution already plans to the earlier of the two dates, so the exposure is limited to a kick-off slip or a milestone dispute. ((G) Project Schedule, p. 7 [S15.2]; Task 1: Project Management, p. 8 [S19.1])

**Mitigation:** State in the proposal that the DMP will be delivered within two weeks of kick-off and no later than 12/4/2024, and ask MoDOT to confirm which date governs if the kick-off moves.

**Related requirements:** R034, R047, R048.

### K12. Interim presentation date conflicts with the mid-point requirement

The RFP requires the interim presentation near the project mid-point and also by 9/15/2025, which is roughly ten months into a fifteen-month contract. The solution schedules to 9/15/2025, but if MoDOT later insists on a true mid-point date the presentation, and the reporting cadence around it, must be re-planned.

**Why:** The solution already resolves the conflict in the safer direction, so the impact is a rescheduling cost rather than a missed obligation. ((G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])

**Mitigation:** State in the proposal that the interim presentation is delivered by 9/15/2025 and treat that date as the binding one; ask MoDOT to confirm at kick-off.

**Related requirements:** R030, R037.

## Referenced documents

| Name | Kind | Page | Section | In PDF | URL |
|---|---|---|---|---|---|
| Exhibit A | exhibit | 15 | SECTION (5): AGREEMENT REQUIREMENTS | no |  |
| Exhibit B | exhibit | 15 | SECTION (5): AGREEMENT REQUIREMENTS | no |  |
| https://www.modot.org/information-researchers | hyperlink | 1 |  | no | https://www.modot.org/information-researchers |
| Section | hyperlink | 5 | GENERAL DESCRIPTION AND BACKGROUND | no | https://epg.modot.org/index.php/236.4_Description_Writing_and_Titles#236.4.6.2_Methods_of_Legally_Describing_the_Fee_or_Portion_Thereof |
| https://www.modot.org/research- | hyperlink | 6 | GENERAL DESCRIPTION AND BACKGROUND | no | https://www.modot.org/research-requests-proposal |
| Data Management Plan | hyperlink | 8 | Project Management | no | https://www.modot.org/media/14044 |
| https://www.e-verify.gov/ | hyperlink | 15 | SECTION (5): AGREEMENT REQUIREMENTS | no | https://www.e-verify.gov/ |
| .NET and .NET Core official | hyperlink | 17 | SECTION (5): AGREEMENT REQUIREMENTS | no | https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core |
| State of Missouri's | hyperlink | 18 | SECTION (5): AGREEMENT REQUIREMENTS | no | https://at.mo.gov/it-access/ |
| Accessibility (mo.gov)). | hyperlink | 18 | SECTION (5): AGREEMENT REQUIREMENTS | no | https://www.mo.gov/accessibility/ |
| (WCAG 2.1 AA). | hyperlink | 18 | SECTION (5): AGREEMENT REQUIREMENTS | no | https://www.w3.org/TR/WCAG21/ |

## Parse flags

- Page 19: low word count (19 words)
- Page 19: large image block (image covers 54% of the page)
- Page 20: low word count (19 words)
- Page 20: large image block (image covers 54% of the page)
