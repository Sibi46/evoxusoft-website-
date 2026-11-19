const menu=document.querySelector('.menu'),nav=document.querySelector('nav');menu.addEventListener('click',()=>{const open=nav.classList.toggle('open');menu.setAttribute('aria-expanded',String(open));menu.textContent=open?'×':'☰'});nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{nav.classList.remove('open');menu.setAttribute('aria-expanded','false');menu.textContent='☰'}));
const fields={marketing:{label:'IDEAS INTO IMPACT',title:'Good thinking.<br>Real business growth.',description:'Turn creativity into commercial value. Build practical experience in marketing strategy, branding, customer development, and business consulting.',tags:['Brand strategy','Market development','Consulting'],photo:'photo-1552664730-d307ca884978',alt:'Team planning a business strategy',cta:'Explore marketing opportunities',interest:'Business Consulting'},digital:{label:'BUILT FOR WHAT’S NEXT',title:'Digital thinking.<br>New possibilities.',description:'Explore digital marketing, content, automation, and technology-enabled services. Connect creative ideas with practical tools for modern business.',tags:['Digital marketing','Content creation','Automation'],photo:'photo-1516321318423-f06f85e504b3',alt:'People working together with digital tools',cta:'Explore digital opportunities',interest:'Entrepreneurship Opportunities'},agriculture:{label:'GROW SOMETHING MEANINGFUL',title:'Fresh ideas.<br>Stronger rural futures.',description:'Connect agriculture with technology, market access, and enterprise. Explore agricultural services and business opportunities that support rural economies.',tags:['Agricultural enterprise','Market access','Rural innovation'],photo:'photo-1500382017468-9049fed747ef',alt:'Green agricultural fields in the countryside',cta:'Explore agripreneurship',interest:'Agripreneurship'},community:{label:'OPPORTUNITY STARTS LOCALLY',title:'Connected people.<br>Thriving communities.',description:'Help local businesses, institutions, and people connect through rural and urban media networks, neighbourhood marketing, and entrepreneurship awareness.',tags:['Local business','Community networks','Institutional partnerships'],photo:'photo-1517245386807-bb43f82c33c4',alt:'People connecting in a community workspace',cta:'Explore community opportunities',interest:'Community development'}};
fields.soft={label:'EVOXU SOFT',title:'Build technology.<br>Build your future.',description:'Where young talent meets technology and innovation. Gain practical experience in software development, web and mobile applications, AI, and automation through real-world projects, mentorship, and teamwork.',tags:['Software development','Web & mobile','AI & automation'],photo:'photo-1516321318423-f06f85e504b3',alt:'Technology professionals collaborating on a software project',cta:'Discover EVOXU SOFT',interest:'EVOXU SOFT & Technology',href:'#evoxu-soft'};
const tabs=[...document.querySelectorAll('[role=tab]')];function activate(tab){tabs.forEach(t=>{const active=t===tab;t.setAttribute('aria-selected',String(active));t.tabIndex=active?0:-1});const isSoft=tab.dataset.field==='soft';document.querySelector('#field-panel').hidden=isSoft;document.querySelector('#evoxu-soft').hidden=!isSoft;if(isSoft)return;const f=fields[tab.dataset.field];document.querySelector('#field-label').textContent=f.label;document.querySelector('#field-title').innerHTML=f.title;document.querySelector('#field-description').textContent=f.description;document.querySelector('#field-tags').replaceChildren(...f.tags.map(t=>{const s=document.createElement('span');s.textContent=t;return s}));const img=document.querySelector('#field-photo');img.src=`https://images.unsplash.com/${f.photo}?auto=format&fit=crop&w=1000&q=85`;img.alt=f.alt;const cta=document.querySelector('#field-cta');cta.textContent=f.cta;cta.href=f.href||'#contact';cta.dataset.interest=f.interest;document.querySelector('#field-panel').setAttribute('aria-labelledby',tab.id)}tabs.forEach((tab,i)=>{tab.id=`field-tab-${i}`;tab.setAttribute('aria-controls',tab.dataset.field==='soft'?'evoxu-soft':'field-panel');tab.tabIndex=i===0?0:-1;tab.addEventListener('click',()=>activate(tab));tab.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;activate(tabs[next]);tabs[next].focus()}})});function openHashTab(){if(location.hash==='#evoxu-soft')activate(tabs.find(t=>t.dataset.field==='soft'))}activate(tabs[0]);openHashTab();window.addEventListener('hashchange',openHashTab);document.addEventListener('click',e=>{const link=e.target.closest('[data-interest]');if(link)document.querySelector('#interest').value=link.dataset.interest});
// Use FormSubmit's documented AJAX endpoint; keep the visitor on EVOXU.
const enquiryForm=document.querySelector('#enquiry');
enquiryForm.addEventListener('submit',async(event)=>{
 event.preventDefault();
 const button=enquiryForm.querySelector('button[type="submit"]');
 if(button.disabled)return;
 const status=document.querySelector('#form-status');
 const values=Object.fromEntries(new FormData(enquiryForm));
 if(values._honey){status.textContent='Please leave the empty website field blank and try again.';return;}
 delete values._next;
 values._url='https://www.evoxuind.com/';
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),30000);
 button.disabled=true;button.textContent='Sending...';enquiryForm.setAttribute('aria-busy','true');
 status.className='form-status-pending';status.textContent='Sending your enquiry. Please wait...';
 try{
  const response=await fetch('https://formsubmit.co/ajax/evoxusoft@gmail.com',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(values),signal:controller.signal});
  let result;
  try{result=await response.json();}catch{throw new Error('The email service returned an unexpected response. Please email us directly using the link below.');}
  const message=typeof result.message==='string'?result.message:'';
  if(/activat|confirm.*email|verify.*email/i.test(message)){
   throw new Error('The EVOXU email service is awaiting activation. Please email evoxusoft@gmail.com directly while activation is completed.');
  }
  if(!response.ok){throw new Error(response.status===403?'The email service blocked this submission. Please use the direct email link below.':'The email service is temporarily unavailable. Your form has been kept so you can try again or email us directly.');}
  if(result.success!==true&&result.success!=='true'){
   throw new Error(message?'Enquiry not sent: '+message.slice(0,300):'The email service did not accept your enquiry. Please try again or use the direct email link below.');
  }
  status.className='form-status-success';status.textContent='Your enquiry was accepted for email delivery. Thank you for connecting with EVOXU.';
  enquiryForm.reset();document.querySelector('#application-job').value='';
 }catch(error){
  status.className='form-status-error';
  status.textContent=error.name==='AbortError'?'The email service took too long to respond, so we could not confirm submission. Your details are still here. Please check before retrying or email us directly.':error instanceof TypeError?'We could not connect to the email service. Your details are still here. Please try again or use the direct email link below.':error.message;
 }finally{
  clearTimeout(timeout);button.disabled=false;button.textContent='Send enquiry';enquiryForm.removeAttribute('aria-busy');status.focus();
 }
});
const jobList=document.querySelector('#jobs-list');
async function loadJobs(){
 jobList.replaceChildren();
 const loading=document.createElement('p');loading.className='jobs-message';loading.textContent='Loading current openings...';jobList.append(loading);
 try{
  const response=await fetch('/api/jobs',{headers:{Accept:'application/json'},cache:'no-store'});
  if(!response.ok)throw new Error('Jobs unavailable');
  const data=await response.json();
  if(!Array.isArray(data.jobs))throw new Error('Invalid jobs');
  jobList.replaceChildren();
  if(!data.jobs.length){const empty=document.createElement('p');empty.className='jobs-message';empty.textContent='No openings are published right now. You can still introduce yourself through our enquiry form.';jobList.append(empty);return;}
  for(const job of data.jobs){
   const card=document.createElement('article');card.className='public-job';
   const department=document.createElement('p');department.className='eyebrow';department.textContent=job.department;
   const title=document.createElement('h3');title.textContent=job.title;
   const meta=document.createElement('p');meta.className='job-meta';meta.textContent=job.location+' | '+job.employment_type;
   const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='View job details';
   const description=document.createElement('p');description.className='job-description';description.textContent=job.description;details.append(summary,description);
   const apply=document.createElement('a');apply.className='button';apply.href='#contact';apply.textContent='Apply for this role';
   apply.addEventListener('click',()=>{document.querySelector('#interest').value='Careers & Training';document.querySelector('#application-job').value=job.title;document.querySelector('#form-status').textContent='Applying for: '+job.title;});
   card.append(department,title,meta,details,apply);jobList.append(card);
  }
 }catch(error){jobList.replaceChildren();const msg=document.createElement('p');msg.className='jobs-message';msg.textContent='We could not load current openings. Please try again or contact us about career opportunities.';const retry=document.createElement('button');retry.type='button';retry.className='button';retry.textContent='Try again';retry.addEventListener('click',loadJobs);jobList.append(msg,retry);}
}
loadJobs();
