<!-- QEC:START -->
<picture><source media="(prefers-color-scheme: dark)" srcset="assets/qec/banner-9-dark.svg"><img src="assets/qec/banner-9-light.svg" alt="Amogh D. Prasanna: quantum compilation, error correction, generative QML. UMD and Fermilab SQMS. A shared distance-5 rotated surface code, 0 X and 1 Z errors waiting to be decoded. 3 decodes, 0 logical failures." width="100%"></picture>

<p align="center"><a href="https://github.com/amoghdprasanna/amoghdprasanna/issues/new?title=qec%3A+X&body=Press+Submit.+A+bot+updates+the+surface+code+within+a+minute."><picture><source media="(prefers-color-scheme: dark)" srcset="assets/btn-qec-x-dark.svg"><img src="assets/btn-qec-x-light.svg" alt="Add an X error" height="34"></picture></a>&nbsp;<a href="https://github.com/amoghdprasanna/amoghdprasanna/issues/new?title=qec%3A+Z&body=Press+Submit.+A+bot+updates+the+surface+code+within+a+minute."><picture><source media="(prefers-color-scheme: dark)" srcset="assets/btn-qec-z-dark.svg"><img src="assets/btn-qec-z-light.svg" alt="Add a Z error" height="34"></picture></a>&nbsp;<a href="https://github.com/amoghdprasanna/amoghdprasanna/issues/new?title=qec%3A+decode&body=Press+Submit.+A+bot+updates+the+surface+code+within+a+minute."><picture><source media="(prefers-color-scheme: dark)" srcset="assets/btn-qec-decode-dark.svg"><img src="assets/btn-qec-decode-light.svg" alt="Decode" height="34"></picture></a>&nbsp;<a href="https://github.com/amoghdprasanna/amoghdprasanna/issues/new?title=qec%3A+reset&body=Press+Submit.+A+bot+updates+the+surface+code+within+a+minute."><picture><source media="(prefers-color-scheme: dark)" srcset="assets/btn-qec-reset-dark.svg"><img src="assets/btn-qec-reset-light.svg" alt="Reset the code" height="34"></picture></a></p>
<!-- QEC:END -->

I'm a graduate researcher at the University of Maryland, working with Prof. Shabnam Jabeen and, at Fermilab's SQMS center, Dr. Tanay Roy. I care about the gap between the circuit we write and what the hardware actually does.

This page is not a résumé. It says why each repository here exists: the question, or the small annoyance, that made the code worth writing.

<a href="https://amoghdprasanna.github.io/"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/btn-website-dark.svg"><img src="assets/btn-website-light.svg" alt="Website" height="34"></picture></a>&nbsp;
<a href="https://www.linkedin.com/in/amogh-d-p"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/btn-linkedin-dark.svg"><img src="assets/btn-linkedin-light.svg" alt="LinkedIn" height="34"></picture></a>&nbsp;
<a href="mailto:amoghdp@umd.edu"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/btn-email-dark.svg"><img src="assets/btn-email-light.svg" alt="Email amoghdp@umd.edu" height="34"></picture></a>

<br>

<picture><source media="(prefers-color-scheme: dark)" srcset="assets/hdr-why-dark.svg"><img src="assets/hdr-why-light.svg" alt="01. Why this code is here" width="100%" height="44"></picture>

**Can a quantum circuit learn how quarks become hadrons?**<br>
<sub>`qml_hadronization` &nbsp;·&nbsp; private group repo, write-up in progress &nbsp;·&nbsp; Qiskit, JAX, Pythia 8</sub>

There is no first-principles calculation of hadronization, so event generators like Pythia fit a phenomenological Lund string model instead. I train quantum circuit Born machines on Pythia 8 momentum distributions and check what survives once IBM's noise model is switched on. The lesson so far is that on noisy hardware the budget is two-qubit gates, not depth: my best circuit under FakeBrisbane noise uses only 32 native ECR gates.

**Can I ask about *this* equation without leaving the page?**<br>
<sub>[`marginalia`](https://github.com/amoghdprasanna/marginalia) &nbsp;·&nbsp; Python, Qt, Claude API</sub>

I read papers and watch lectures most of the day, and every question used to mean copying an equation into another window. marginalia floats over the screen: ask about whatever you're looking at, and markers fly to the symbols the answer is about. The hard part was making them land on the right pixels. It resizes each screenshot itself, so the model's coordinates map one to one onto the image it saw and back to the screen, then snaps each point onto the OCR line it names. Every question is saved to a dated journal of doubts.

**What does a veteran technician know that the manual doesn't?**<br>
<sub>[`HVAC Copilot`](https://github.com/Rayhanpatel/Ycombinator-Cactus-Deepmind) &nbsp;·&nbsp; YC × Cactus × DeepMind hackathon, team project &nbsp;·&nbsp; on-device Gemma</sub>

A team-built, on-device voice assistant for HVAC technicians. My part was the search behind it: when the manual's answer doesn't fix the unit, look further, into forums. I wrote a ranker, unit-tested but not yet wired into the app, that lets a certified tech's deeply nested reply outrank the official support page by weighing author expertise, reply depth and "this fixed mine" replies against source authority.

**What does a threat model actually change in the code?**<br>
<sub>[`Threat-Model-Dunder-Mifflin`](https://github.com/amoghdprasanna/Threat-Model-Dunder-Mifflin) &nbsp;·&nbsp; UMD ENPM680 &nbsp;·&nbsp; Go, Fiber, PostgreSQL</sub>

A course project that takes a plain inventory app through misuse cases and STRIDE. 29 threats became 38 security requirements, and the code cites 27 of them by ID. The clearest change: a role-tampering threat moved roles out of client-held tokens and into server-side sessions that are reloaded on every request.

**What does ATAK do with a unit that actually moves?**<br>
<sub>[`ATAK-CDCL`](https://github.com/amoghdprasanna/ATAK-CDCL) &nbsp;·&nbsp; Java, Android TAK SDK</sub>

TAK's stock CoT injector only scatters static markers. I added a simulated GPS unit that drives line, circle and square paths at a set speed and is sent through ATAK's internal dispatcher, so the map treats it like a real GPS-reported friendly unit and draws its trace.

<br>

<picture><source media="(prefers-color-scheme: dark)" srcset="assets/hdr-now-dark.svg"><img src="assets/hdr-now-light.svg" alt="02. Open questions" width="100%" height="44"></picture>

**Can a learned compiler beat analytic decompositions on a qudit?** With Dr. Tanay Roy (Fermilab SQMS) I'm training models that compile arbitrary SU(*d*) unitaries into native gate sequences for superconducting transmon qudits, with leakage and anharmonicity built into the objective rather than patched on afterwards.

**Decoding topological codes.** I'm contributing to an open-source toolkit, in Python and C++, for simulating and decoding them.

<br>

<sub>The banner is a distance-5 rotated surface code shared by every visitor: add X or Z errors, watch the stabilizers that catch them light up, then decode and see whether the logical qubit survived. Everything on this page is drawn by the code in this repository.</sub>
