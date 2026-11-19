const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {test}=require('node:test');
const source=fs.readFileSync('dist/app.js','utf8');
const handler=source.slice(source.indexOf('// Use FormSubmit'),source.indexOf('const jobList='));

function setup(fetchResponse){
 const button={disabled:false,textContent:'Send enquiry'};
 const status={textContent:'',className:'',focus(){}};
 const application={value:'Software Intern'};
 let listener,resetCount=0,requests=[];
 const form={querySelector(){return button},addEventListener(type,fn){listener=fn},setAttribute(){},removeAttribute(){},reset(){resetCount++}};
 const values={name:'Example visitor',email:'visitor@example.com',message:'A test enquiry',_honey:'','Job application':'Software Intern'};
 const context={document:{querySelector(selector){return {'#enquiry':form,'#form-status':status,'#application-job':application}[selector]}},FormData:class{constructor(){return Object.entries(values)}},AbortController,setTimeout,clearTimeout,TypeError,fetch:async(url,options)=>{requests.push({url,options});if(fetchResponse instanceof Error)throw fetchResponse;return fetchResponse}};
 vm.runInNewContext(handler,context);
 return {submit:()=>listener({preventDefault(){}}),status,button,requests,application,get resetCount(){return resetCount}};
}

test('accepted submission stays in-page and resets only after explicit success',async()=>{
 const page=setup({ok:true,status:200,json:async()=>({success:'true',message:'The form was submitted successfully.'})});
 await page.submit();
 assert.equal(page.resetCount,1);
 assert.match(page.status.textContent,/accepted for email delivery/);
 assert.equal(page.application.value,'');
 assert.equal(page.requests[0].url,'https://formsubmit.co/ajax/evoxusoft@gmail.com');
 assert.equal(JSON.parse(page.requests[0].options.body)._url,'https://www.evoxuind.com/');
 assert.equal(page.button.disabled,false);
});

test('pending activation is shown clearly and does not discard input',async()=>{
 const page=setup({ok:true,status:200,json:async()=>({success:false,message:'Please activate your form. Check your email.'})});
 await page.submit();
 assert.equal(page.resetCount,0);
 assert.match(page.status.textContent,/awaiting activation/);
 assert.equal(page.status.className,'form-status-error');
});

test('HTTP 403 is not treated as a submitted enquiry',async()=>{
 const page=setup({ok:false,status:403,json:async()=>({message:'Forbidden'})});
 await page.submit();
 assert.equal(page.resetCount,0);
 assert.match(page.status.textContent,/blocked this submission/);
 assert.equal(page.button.disabled,false);
});

test('network errors keep details and expose the direct-email fallback message',async()=>{
 const page=setup(new TypeError('Failed to fetch'));
 await page.submit();
 assert.equal(page.resetCount,0);
 assert.match(page.status.textContent,/could not connect/);
});

test('malformed provider response never reports success',async()=>{
 const page=setup({ok:true,status:200,json:async()=>{throw new Error('Not JSON')}});
 await page.submit();
 assert.equal(page.resetCount,0);
 assert.match(page.status.textContent,/unexpected response/);
});

test('duplicate clicks do not create a second request',async()=>{
 let release;
 const response={ok:true,status:200,json:()=>new Promise(resolve=>{release=resolve})};
 const page=setup(response);
 const pending=page.submit();
 await new Promise(resolve=>setImmediate(resolve));
 await page.submit();
 assert.equal(page.requests.length,1);
 release({success:true});
 await pending;
});
