# **SELENE: Privacy-First AI for Menopause Support**

**Grounded in Science. Built for Trust. Designed for Real-World Care.**

---

## **Your team**

Inna Campo. I am a multidisciplinary AI practitioner with experience in medical informatics, privacy-preserving AI design, and product architecture. I led every aspect of SELENE’s conception and development, including problem definition, system design, model integration using MedGemma from the HAI-DEF collection, privacy and ethical framing, and product narrative. 

---

## **Problem statement**

### **Menopause Care Lacks High-Fidelity Evidence**

Menopause affects a significant portion of the population and is associated with a wide range of symptoms that vary in intensity, duration, and presentation. However, clinical guidelines are often based on small, short-term studies that do not reflect the lived experience of women navigating a multi-year transition. Many women experience anxiety, sleep disruption, musculoskeletal symptoms, cognitive changes, and cardiovascular concerns that do not align well with narrow clinical definitions. Because longitudinal real-world evidence is scarce, clinicians frequently lack access to structured, multi-year symptom patterns that could inform care conversations and reduce guesswork.

### **Centralized AI Is Not a Realistic Answer**

While large cloud-based AI models have proliferated, they are inappropriate for many clinical and care contexts due to privacy, connectivity, and infrastructure limitations. In healthcare environments where data protection is essential and network access cannot be assumed, cloud-dependent solutions introduce unacceptable risk and reduce trust. Furthermore, static models trained on fixed datasets fail to incorporate evolving scientific research, limiting their usefulness in domains like women’s health where evidence is rapidly emerging.

### **Impact Potential**

SELENE aims to bridge this evidence gap by enabling women to track and contextualize their symptoms over time, grounding those insights in current medical research while preserving privacy and control. By improving the quality of longitudinal symptom interpretation, SELENE has the potential to enhance patient-clinician dialogue, reduce misclassification of symptoms, and contribute to a more comprehensive evidence base for menopause care. Even modest improvements in clinical clarity and shared understanding could positively affect millions of clinical interactions globally.

---

## **Overall solution**

### **A Privacy-First, MedGemma-Powered Medical Intelligence Engine**

SELENE is a privacy-first AI system built around **MedGemma**, an open-weight medical language model from Google’s HAI-DEF collection. MedGemma serves as SELENE’s core reasoning engine, providing medically grounded interpretation of symptoms, clinical language, and research context. Unlike closed, cloud-dependent models, MedGemma can run locally and be fully controlled by the application, enabling SELENE to deliver evidence-aligned guidance without transmitting sensitive user data to a server.

### **Grounding Answers in Current Research**

Rather than relying only on the model’s pre-trained knowledge, SELENE consults a locally stored library of peer-reviewed research and clinical guidelines before generating responses. This ensures that answers reflect both MedGemma’s medical reasoning capabilities and the latest scientific evidence. Importantly, all retrieval and generation are performed on the user’s device, preserving privacy and enabling offline operation.

### **Privacy-Preserving Updates**

SELENE keeps its medical knowledge current through one-way updates: small, regularly released bundles of new research summaries that merge into the local knowledge base without requiring any user data to be shared. This means medical guidance remains in step with evolving clinical understanding while user behavior and personal logs remain fully local.

### **Citizen Scientist Participation (Optional)**

SELENE also offers users the option to contribute anonymized, aggregated insights that help illuminate longitudinal symptom patterns across a broader population. Participation is explicit, granular, and reversible, and does not involve transmitting personal data. This citizen science model helps create higher-resolution real-world evidence that can inform future research and clinician education without compromising individual privacy.

Together, these design choices make SELENE an AI system that uses HAI-DEF models effectively, respects data sovereignty, and grounds insights in current science — addressing the limitations that traditional clinical tools and centralized AI systems face.

---

## **Technical details**

### **Feasibility Within Real-World Constraints**

SELENE’s architecture is designed to be operationally realistic. At its core, the system performs all inference and retrieval locally on the user’s device, without requiring constant connectivity. This design supports environments where internet access may be intermittent or where cloud dependency is unacceptable for sensitive health information.

MedGemma is integrated as the local reasoning model because it is trained on biomedical and clinical corpora, enabling nuanced understanding of medical terminology and guideline language. Retrieval takes place against a locally stored, encrypted library of peer-reviewed research and clinical guidance, ensuring that evidence remains authoritative and up-to-date.

### **Local Retrieval and Knowledge Updates**

Before generating any answer, SELENE retrieves relevant medical context from the encrypted on-device library of research summaries. This prioritizes mechanism-based and explanatory content over simple keyword matching, aligning with clinical reasoning patterns rather than surface associations.

The research library is updated through a pull-only system that delivers incremental knowledge patches derived from newly published studies. This mechanism preserves the “no phone home” privacy guarantee: while SELENE can receive updated research content, it never transmits user queries, interaction data, or personal logs.

### **Deployment and Product Experience**

From a product feasibility perspective, SELENE emphasizes usability, clarity, and calm engagement. The UI is optimized for legibility and minimal cognitive load, catering to diverse symptom states. Encryption and privacy controls are foregrounded so users always understand how their data is managed. SELENE also provides clinician-ready summaries that organize longitudinal symptom data into structured formats conducive to shared decision-making.

Detailed architectural diagrams, reproducible code for local inference and retrieval, and configuration notes for model deployment are provided in the accompanying technical documentation. These support reproducibility and demonstrate a path to real-world application beyond the competition context.