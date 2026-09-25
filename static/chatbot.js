const chatWidget = document.getElementById("chatWidget")
const chatToggle = document.getElementById("chatToggle")
const chatBody = document.getElementById("chatBody")
const input = document.getElementById("messageInput")
const HISTORY_KEY = "nsdc-chat-history"
const NSDC_BASE = "https://skillindiadigital.gov.in"

function toggleChat(){
  chatWidget.classList.toggle("collapsed")
}

chatToggle.addEventListener("click",toggleChat)

function scrollBottom(){
  chatBody.scrollTop = chatBody.scrollHeight
}

function save(msg){
  const history = JSON.parse(sessionStorage.getItem(HISTORY_KEY)||"[]")
  history.push(msg)
  sessionStorage.setItem(HISTORY_KEY,JSON.stringify(history))
}

function addMessage(text, sender, meta = {}, persist = true){
  const div = document.createElement("div")
  div.className = sender === "user" ? "user-message" : "bot-message"

  const message = document.createElement("div")
  message.className = "message-text"
  message.textContent = text
  div.appendChild(message)

  if(sender === "bot" && meta.course_cards){
    const cards = document.createElement("div")
    cards.className = "chat-course-cards"
    meta.course_cards.forEach(course => {
      const card = document.createElement("a")
      card.className = "chat-course-card"
      card.href = `/course/${encodeURIComponent(course.id)}`
      card.innerHTML = `<strong>${course.title}</strong><span>${course.category} · ${course.duration}</span><small>${course.level} <b>View Details →</b></small>`
      cards.appendChild(card)
    })
    div.appendChild(cards)
  }

  if(sender === "bot" && meta.source){
    const source = document.createElement("div")
    source.className = "source"
    source.textContent = `${meta.category || "NSDC"} • ${meta.source}`
    div.appendChild(source)
  }

  if(sender === "bot" && meta.page){
    const link = document.createElement("a")
    link.className = "page-link"
    link.href = NSDC_BASE + meta.page
    link.target = "_blank"
    link.rel = "noopener noreferrer"
    let buttonText = "Open Page"
    if(meta.page.includes("courses")) buttonText = "Explore Courses"
    else if(meta.page.includes("registration")) buttonText = "Register Now"
    else if(meta.page.includes("ekyc")) buttonText = "Complete e-KYC"
    else if(meta.page.includes("dashboard")) buttonText = "Open Dashboard"
    else if(meta.page.includes("support")) buttonText = "Get Support"
    link.innerHTML = `${buttonText} ↗`
    div.appendChild(link)
  }

  chatBody.appendChild(div)
  if(persist) save({text, sender, meta})
  scrollBottom()
}

function typing(){
  const div=document.createElement("div")
  div.id="typing"
  div.className="bot-message typing"
  div.innerHTML="<span></span><span></span><span></span>"
  chatBody.appendChild(div)
  scrollBottom()
}

function removeTyping(){
  const typingMessage=document.getElementById("typing")
  if(typingMessage) typingMessage.remove()
}

async function sendMessage(){
  const message=input.value.trim()
  if(!message) return
  addMessage(message,"user")
  input.value=""
  typing()
  try{
    const res=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message})})
    const data=await res.json()
    removeTyping()
    addMessage(data.answer,"bot",data)
  }catch(e){
    removeTyping()
    addMessage("The assistant is currently unavailable.","bot")
  }
}

function quickAsk(question){
  input.value=question
  sendMessage()
}

input.addEventListener("keypress",(event)=>{
  if(event.key==="Enter") sendMessage()
})

const history=JSON.parse(sessionStorage.getItem(HISTORY_KEY)||"[]")
history.forEach(message=>addMessage(message.text,message.sender,message.meta,false))