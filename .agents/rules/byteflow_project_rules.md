# ByteFlow Project Rules & Software Engineering Guidelines

## 1. Project Context
- **Project Name:** ByteFlow: A Comparative Platform for Classical and Quantum Max-Cut Solutions
- **Course:** CSC 312 – Software Engineering Group Project (2026)
- **Institution:** University of the Western Cape (UWC)
- **Lecturer:** Dr. M.J. Norman

---

## 2. Core SE Directives & Academic Constraints
1. **Process & Quality over Complexity:** The lecturer prioritizes adherence to the Software Engineering lifecycle (SDLC), clean architecture, ISO 25010 software quality attributes, and documentation rigor over algorithmic complexity.
2. **Submission Constraints:**
   - Permitted deliverable formats: **PDF** (documents, code in PDF) and **MP4** (videos).
   - **Strict Negative Constraint:** Absolutely **NO ZIP or DOC files**.
   - Video Deliverables: Max 3-minute application demo (MP4), max 5-minute project presentation (MP4).
3. **Mandatory Documentation Sections:**
   - **Testing:** Formal testing strategy (Pressman Ch. 22: Unit, Integration, Validation, Usability).
   - **Reflection on the SE Process:** Candid assessment of Agile/Scrum team dynamics and lessons learned.

---

## 3. ByteFlow System Architecture & Use Case Invariants
1. **Mental Model:** "Virtual Laboratory" workflow divided into 5 stages:
   - *Experiment* (graph selection & algorithm parameterization)
   - *Connection* (IBM Quantum Cloud API authentication)
   - *Execution* (classical & quantum execution)
   - *Fallback* (automatic local simulator redirection on failure/timeout)
   - *Analytics* (side-by-side comparative benchmarking)
2. **Core Use Cases (UC1 – UC5):**
   - **UC1 (Classical Solver):** Deterministic baseline (Greedy local search / SDP approximation).
   - **UC2 (Quantum Execution):** Parameterized QAOA ansatz ($p \ge 1$, $\gamma, \beta$) executed on IBM Quantum hardware via Qiskit Runtime Sampler.
   - **UC3 (Fallback Handling):** Essential fault tolerance. Dynamic redirection to local simulator (`qiskit_aer` or `StatevectorSampler`) upon auth errors or queue timeouts, tagging `provenance_label` ('IBM QPU' vs. 'Local Sim').
   - **UC4 (Configuration & Security):** Secure token handling and experiment parameterization (graph instances, shot counts, layer depth $p$).
   - **UC5 (Comparative Analytics):** Dual-channel visualization displaying partition cut values, approximation ratios, wall-clock time, and measurement distributions.
3. **Educational Graph Focus:** Provide manageable demonstration graphs (e.g. 4-node diamond, 5-node ring, 8-node custom/Petersen graphs) in addition to large topologies so students can visualize partitions intuitively.
