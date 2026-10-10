"""Every text run of posts 04-06 (exact strings, colour, and a search box in
grid-panel px used only to fit the run's placement). One run = one colour."""
NAVY = (0x00, 0x30, 0x49)
CREAM = (0xFC, 0xF0, 0xD6)
RED = (0xC1, 0x12, 0x1F)
RUNS = {
    "POST_04": [
        dict(id="p4_l1", text="مو بس جاكيت...", colour="navy", box=(215, 100, 625, 170)),
        dict(id="p4_hay", text="هاي", colour="navy", box=(462, 750, 625, 840)),
        dict(id="p4_word", text="ذكرياتك", colour="red", box=(165, 750, 470, 840), embroidered=True),
        dict(id="p4_dot", text=".", colour="red", box=(140, 785, 172, 822)),
    ],
    "POST_05": [
        dict(id="p5_l1", text="إنت اختار", colour="cream", box=(370, 75, 640, 150)),
        dict(id="p5_kul", text="كل", colour="cream", box=(515, 155, 635, 228)),
        dict(id="p5_word", text="تفصيلة", colour="red", box=(318, 155, 515, 228), embroidered=True),
        dict(id="p5_dot", text=".", colour="red", box=(288, 186, 318, 226)),
        dict(id="p5_sub", text="إنت تصمّم، وإحنا ننفّذ.", colour="cream", box=(345, 238, 635, 285)),
        dict(id="p5_bottom", text="لونك، أحرفك، وتطريزك... على ذوقك.", colour="cream", box=(318, 818, 645, 862)),
    ],
    "POST_06": [
        dict(id="p6_l1", text="كل تفصيلة", colour="navy", box=(240, 640, 630, 730)),
        dict(id="p6_ilha", text="إلها", colour="navy", box=(468, 755, 630, 845)),
        dict(id="p6_word", text="معنى", colour="red", box=(355, 755, 470, 845), embroidered=True),
    ],
}
