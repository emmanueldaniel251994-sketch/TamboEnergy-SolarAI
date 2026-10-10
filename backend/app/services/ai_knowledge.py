GUIDES = {
"battery": ("KB-BATTERY","Battery checks","Check charging availability, state of charge and recorded voltage against the specific manufacturer's manual."),
"inverter": ("KB-INVERTER","Inverter fault checks","Record the make, model and error code; consult the matching manual. Do not open energized equipment."),
"solar": ("KB-PV","Solar generation checks","Compare production with sunlight, shading and historic trends. Do not touch energized PV wiring."),
"temperature": ("KB-THERMAL","Overheating checks","Check accessible ventilation and arrange qualified inspection for overheating."),
}
def retrieve(question):
    q=question.lower()
    return [{"id":v[0],"title":v[1],"text":v[2]} for k,v in GUIDES.items() if k in q][:3]
