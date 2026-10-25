document.addEventListener("DOMContentLoaded", () => {
  const dataTag = document.getElementById("section-data");
  const levelSelect = document.getElementById("manageLevel");
  const programSelect = document.getElementById("manageProgram");
  const sectionSelect = document.getElementById("manageSection");
  if (dataTag && levelSelect && programSelect && sectionSelect) {
    const data = JSON.parse(dataTag.textContent);
    function fillPrograms() {
      const level = levelSelect.value;
      programSelect.innerHTML = "";
      Object.keys(data[level] || {}).forEach(program => {
        const opt = document.createElement("option");
        opt.value = program; opt.textContent = program; programSelect.appendChild(opt);
      });
      fillSections();
    }
    function fillSections() {
      sectionSelect.innerHTML = "";
      (data[levelSelect.value]?.[programSelect.value] || []).forEach(section => {
        const opt = document.createElement("option");
        opt.value = section; opt.textContent = section; sectionSelect.appendChild(opt);
      });
    }
    levelSelect.addEventListener("change", fillPrograms);
    programSelect.addEventListener("change", fillSections);
    fillPrograms();
  }
  const timetableLevel = document.getElementById("levelSelect");
  const timetableProgram = document.getElementById("programSelect");
  if (timetableLevel && timetableProgram) {
    const sectionData = JSON.parse(document.getElementById("timetable-section-data")?.textContent || "{}");
    timetableLevel.addEventListener("change", () => {
      const programs = Object.keys(sectionData[timetableLevel.value] || {});
      timetableProgram.innerHTML = "";
      programs.forEach(p => {
        const opt = document.createElement("option"); opt.value = p; opt.textContent = p; timetableProgram.appendChild(opt);
      });
    });
  }
});

// SHS-specific teacher and subject choices. The server independently validates these values.
document.addEventListener('DOMContentLoaded', () => {
  const level = document.getElementById('manageLevel');
  const program = document.getElementById('manageProgram');
  const section = document.getElementById('manageSection');
  const teacher = document.getElementById('manageTeacher');
  const subject = document.getElementById('manageSubject');
  const dataNode = document.getElementById('section-data');
  if (!level || !program || !section || !dataNode) return;
  const groups = JSON.parse(dataNode.textContent);
  const jhsTeachers = ["Amelia Lopez", "Ronald Domingo", "Jomalyn Caparal", "Precious Pascua", "Cornelio Marquez", "Nemencio Muralla", "Elaiza Vinluan", "Vicky Morales", "Jayjay Grospe", "Maureen Angeles", "Aprilyn Pascua", "Marisol Quiming", "Maribel Pascua", "Conrad Cayanga", "Elvin Alcaide", "Lester Peralta", "Arlene Mendillo"];
  const shsTeachers = ["May Sebido", "Alvin Cunanan", "Elvin Alcaide", "Jenna Granada", "Bryan Esmeria", "Marlon Santiago", "Mary Joy Bruan", "Rhea Joy Vallejos"];
  const jhsSubjects = ["Mathematics","English","Science","Araling Panlipunan","TLE","MAPEH","Filipino","Computer"];
  const shsSubjects = ["Effective Communication", "General Science", "General Mathematics", "Life and Career Skills", "Mabisang Komunikasyon", "Pag-aaral ng Kasaysayan at Lipunang Pilipino", "Introduction to Philosophy", "Introduction to Organization and Management", "Citizenship and Civic Engagement", "Biology 1", "Biology 2", "Advanced Mathematics 1", "Filipino 1 (Wika at Komunikasyon sa Akademikong Filipino)", "Filipino 2 (Filipino para sa Larang Teknikal-Propesyonal)", "Social Sciences (Theory and Practice)", "Entrepreneurship", "Philippine Governance (Philippine Politics and Governance)", "Leadership Management in the Arts", "Contemporary Literature 1", "Contemporary Literature 2", "Empowerment Technologies", "Pre-calculus 1", "Pre-Calculus 2", "Advanced Mathematics 2", "Chemistry 1", "Chemistry 2", "Physics 1", "Physics 2", "Computer System Servicing", "Computer Programming (.NET Technology)", "Visual Graphic Design", "Kitchen Operation", "Events Management Services", "Bakery Operation"];
  function fill(select, values) { const old=select.value; select.innerHTML=''; values.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;select.appendChild(o)}); if(values.includes(old)) select.value=old; }
  function update() {
    const lev=level.value; const programs=groups[lev]||{};
    fill(program,Object.keys(programs));
    fill(section,programs[program.value]||[]);
    if (teacher && subject) {
      fill(teacher,lev==='Senior High School'?shsTeachers:jhsTeachers);
      fill(subject,lev==='Senior High School'?shsSubjects:jhsSubjects);
    }
  }
  level.addEventListener('change',update); program.addEventListener('change',()=>fill(section,(groups[level.value]||{})[program.value]||[])); update();
});


// Use the correct timetable periods for the selected school level.
document.addEventListener('DOMContentLoaded', () => {
  const level = document.getElementById('manageLevel');
  const slotSelect = document.getElementById('manageSlot');
  const dataNode = document.getElementById('slot-data');
  if (!level || !slotSelect || !dataNode) return;
  const data = JSON.parse(dataNode.textContent);
  function updateSlots() {
    const config = level.value === 'Senior High School' ? data.shs : data.jhs;
    slotSelect.innerHTML = '';
    config.slots.forEach(slot => {
      const option = document.createElement('option');
      option.value = slot;
      option.textContent = config.breaks[slot] ? `${slot} — ${config.breaks[slot]} (break)` : slot;
      option.disabled = Boolean(config.breaks[slot]);
      slotSelect.appendChild(option);
    });
    const firstClass = Array.from(slotSelect.options).find(option => !option.disabled);
    if (firstClass) slotSelect.value = firstClass.value;
  }
  level.addEventListener('change', updateSlots);
  updateSlots();
});
