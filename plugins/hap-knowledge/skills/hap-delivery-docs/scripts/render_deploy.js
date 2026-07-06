// 将部署文档快照(markdown)渲染为 docx。样式：Letter、Arial、页眉页脚、标题层级、表格、命令块。
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, ExternalHyperlink
} = require("docx");

const arg = process.argv.slice(2);
const SRC = arg[0];        // markdown 文件
const OUT = arg[1];        // docx 输出
const DOCNAME = arg[2];    // 页脚文档名，如 "部署实施文档（集群标准版）"

let md = fs.readFileSync(SRC, "utf8");
// 封面参数通过环境变量传入
const COVER_TITLE = process.env.COVER_TITLE || DOCNAME;
const COVER_EN = process.env.COVER_EN || "";
const COVER_DATE = process.env.COVER_DATE || "";
const lines = md.split("\n");

const BRAND = "1F5FBF", BRANDD = "16407F", INK = "1A1A1A", GREY = "6B6B6B";
const LINE = "C9D4E5", THBG = "1F5FBF", ALT = "EEF3FB", CODEBG = "F4F6F9";
const CW = 9360; // Letter 内容宽

const children = [];

// ---- 封面页占位（实际封面由后处理脚本注入附件首页 XML，1:1 照搬）----
children.push(new Paragraph({children:[new TextRun({text:"__COVER_PLACEHOLDER__",size:2})]}));
children.push(new Paragraph({children:[new (require("docx").PageBreak)()]}));

// ---- 解析辅助 ----
function isTableSep(l){ return /^\|[\s:|-]+\|?\s*$/.test(l.trim()) && l.includes("-"); }
function splitRow(l){
  let s=l.trim();
  if(s.startsWith("|")) s=s.slice(1);
  if(s.endsWith("|")) s=s.slice(0,-1);
  return s.split("|").map(c=>c.trim());
}
function runsFromText(t){
  // 处理 **bold** 和 链接
  const runs=[];
  // 先拆链接 url
  const parts=t.split(/(https?:\/\/[^\s)）]+)/g);
  for(const p of parts){
    if(/^https?:\/\//.test(p)){
      runs.push(new ExternalHyperlink({children:[new TextRun({text:p,style:"Hyperlink",size:16})],link:p}));
    } else {
      // 处理 **bold**
      const seg=p.split(/(\*\*[^*]+\*\*)/g);
      for(const s of seg){
        if(!s) continue;
        if(s.startsWith("**")&&s.endsWith("**")) runs.push(new TextRun({text:s.slice(2,-2),bold:true}));
        else runs.push(new TextRun(s.replace(/\*\*/g,"")));
      }
    }
  }
  return runs.length?runs:[new TextRun(t)];
}
const border={style:BorderStyle.SINGLE,size:1,color:"CCCCCC"};
const borders={top:border,bottom:border,left:border,right:border};

// ===== 代码块"行混乱"根治：净化 + 按行成段 + heredoc-JSON 展开 =====
// 仅对代码内容生效，绝不动正文（正文中文标点是对的）。
function sanitizeCode(s){
  return s
    .replace(/[\u201C\u201D\u201E\u201F\u2033\u3003]/g,'"')  // 各种弯/全角双引号 → "
    .replace(/[\u2018\u2019\u201A\u201B\u2032]/g,"'")        // 各种弯/全角单引号 → '
    .replace(/[\u00A0\u2007\u202F\u3000]/g," ")              // NBSP/窄空格/全角空格 → 普通空格
    .replace(/[\u200B\u200C\u200D\uFEFF]/g,"");              // 零宽字符 → 删除
}
// 把 `cat > xxx.json <<EOF` 后紧跟的单行长 JSON 自动美化为多行（仅当能 JSON.parse 且较长时）
function expandHeredocJson(rows){
  const out=[];
  for(let k=0;k<rows.length;k++){
    const line=rows[k];
    const isCat=/^\s*cat\s*>\s*\S+\.json\s*<<\s*['"]?EOF['"]?\s*$/.test(sanitizeCode(line));
    const next=rows[k+1]!==undefined?sanitizeCode(rows[k+1]).trim():"";
    const nnext=rows[k+2]!==undefined?rows[k+2].trim():null;
    if(isCat && nnext==="EOF" && next.length>80 && /^[\[{]/.test(next)){
      let obj=null; try{ obj=JSON.parse(next); }catch(e){ obj=null; }
      if(obj!==null){
        out.push(line);
        JSON.stringify(obj,null,2).split("\n").forEach(p=>out.push(p));
        out.push(rows[k+2]); // EOF
        k+=2;
        continue;
      }
    }
    out.push(line);
  }
  return out;
}
// 任意代码文本 → 一行一段的 Paragraph[]（净化 + 保留缩进 + 等宽 + 左对齐，空行占位）
function codeParas(text){
  const rows=expandHeredocJson(String(text).replace(/\r\n?/g,"\n").split("\n"));
  return rows.map(r=>{
    const c=sanitizeCode(r);
    return new Paragraph({
      spacing:{after:0,line:240},
      alignment:AlignmentType.LEFT,
      children:[new TextRun({text:c===""?" ":c,font:"Consolas",size:17,color:"1A6B33"})]
    });
  });
}
function codeCell(paras,padTop,padBot){
  return new Table({
    width:{size:CW,type:WidthType.DXA}, columnWidths:[CW], indent:{size:108,type:WidthType.DXA},
    rows:[new TableRow({children:[new TableCell({
      borders, width:{size:CW,type:WidthType.DXA},
      shading:{fill:CODEBG,type:ShadingType.CLEAR},
      margins:{top:padTop,bottom:padBot,left:140,right:140},
      children:paras
    })]})]
  });
}
function codeBlockMulti(text){ return codeCell(codeParas(text),100,100); }
function codeBlock(text){ return codeCell(codeParas(text),80,80); } // 不再把多行压进一个 TextRun

function realTable(rows){
  const ncol=Math.max(...rows.map(r=>r.length));
  const colW=Math.floor(CW/ncol);
  const widths=Array(ncol).fill(colW); widths[ncol-1]=CW-colW*(ncol-1);
  const trs=rows.map((cells,ri)=>{
    while(cells.length<ncol) cells.push("");
    return new TableRow({children:cells.map((c,ci)=>{
      const head=ri===0;
      const isBold=/^\*\*.*\*\*$/.test(c.trim());
      const txt=c.replace(/\*\*/g,"");
      return new TableCell({
        borders, width:{size:widths[ci],type:WidthType.DXA},
        shading:{fill:head?THBG:(ri%2===0?ALT:"FFFFFF"),type:ShadingType.CLEAR},
        margins:{top:60,bottom:60,left:100,right:100},
        children:[new Paragraph({children:[new TextRun({text:txt,bold:head||isBold,
          color:head?"FFFFFF":INK,size:16})]})]
      });
    })});
  });
  return new Table({width:{size:CW,type:WidthType.DXA},columnWidths:widths,indent:{size:108,type:WidthType.DXA},rows:trs});
}

// ---- 主解析循环 ----
let i=0;
while(i<lines.length){
  const l=lines[i];
  const t=l.trim();
  if(t===""){ i++; continue; }

  // 标题
  if(t.startsWith("# ")){ children.push(new Paragraph({heading:HeadingLevel.HEADING_1,children:runsFromText(t.slice(2))})); i++; continue; }
  if(t.startsWith("## ")){ children.push(new Paragraph({heading:HeadingLevel.HEADING_2,children:runsFromText(t.slice(3))})); i++; continue; }
  if(t.startsWith("### ")){ children.push(new Paragraph({heading:HeadingLevel.HEADING_3,children:runsFromText(t.slice(4))})); i++; continue; }

  // 围栏代码块 ```...```
  if(t.startsWith("```")){
    i++;
    const code=[];
    while(i<lines.length && !lines[i].trim().startsWith("```")){ code.push(lines[i]); i++; }
    i++; // 跳过结束围栏
    children.push(codeBlockMulti(code.join("\n")));
    children.push(new Paragraph({children:[new TextRun({text:"",size:6})],spacing:{after:60}}));
    continue;
  }

  // 表格块（连续 | 开头）
  if(t.startsWith("|")){
    const block=[];
    while(i<lines.length && lines[i].trim().startsWith("|")){ block.push(lines[i]); i++; }
    // 分离分隔行
    const dataRows=block.filter(b=>!isTableSep(b)).map(splitRow);
    if(dataRows.length===0){ continue; }
    const ncol=Math.max(...dataRows.map(r=>r.length));
    if(ncol===1){
      // 单列 = 命令/代码块
      codeJoin(dataRows.map(r=>r[0]).join("\n")).forEach(x=>children.push(x));
    } else {
      children.push(realTable(dataRows));
    }
    children.push(new Paragraph({children:[new TextRun({text:"",size:6})],spacing:{after:60}}));
    continue;
  }

  // 项目符号
  if(t.startsWith("- ")){
    children.push(new Paragraph({numbering:{reference:"bul",level:0},children:runsFromText(t.slice(2))}));
    i++; continue;
  }
  if(/^\d+\.\s/.test(t)){
    children.push(new Paragraph({numbering:{reference:"num",level:0},children:runsFromText(t.replace(/^\d+\.\s/,""))}));
    i++; continue;
  }

  // 普通段落
  children.push(new Paragraph({children:runsFromText(t),spacing:{after:80}}));
  i++;
}

function codeJoin(text){
  // 单元格命令块：每个命令块一个框
  return [codeBlock(text)];
}

// ---- 文档 ----
const doc=new Document({
  styles:{
    default:{document:{run:{font:"Arial",size:21,color:INK}}},
    paragraphStyles:[
      {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,
        run:{size:32,bold:true,color:"2E74B5",font:"Arial"},
        paragraph:{spacing:{before:320,after:160},outlineLevel:0}},
      {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,
        run:{size:26,bold:true,color:"2E74B5",font:"Arial"},
        paragraph:{spacing:{before:220,after:120},outlineLevel:1}},
      {id:"Heading3",name:"Heading 3",basedOn:"Normal",next:"Normal",quickFormat:true,
        run:{size:24,bold:true,color:"1F4D78",font:"Arial"},
        paragraph:{spacing:{before:160,after:80},outlineLevel:2}},
    ]
  },
  numbering:{config:[
    {reference:"bul",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,
      style:{paragraph:{indent:{left:480,hanging:240}}}}]},
    {reference:"num",levels:[{level:0,format:LevelFormat.DECIMAL,text:"%1.",alignment:AlignmentType.LEFT,
      style:{paragraph:{indent:{left:480,hanging:240}}}}]},
  ]},
  sections:[{
    properties:{page:{size:{width:12240,height:15840},margin:{top:1440,right:1440,bottom:1440,left:1440}}},
    headers:{default:new Header({children:[new Paragraph({
      alignment:AlignmentType.RIGHT,
      border:{bottom:{style:BorderStyle.SINGLE,size:4,color:"C9D4E5",space:4}},
      children:[new TextRun({text:"HAP 私有部署 · 交付文档",bold:true,color:"1E5BA8",size:18})]})]})},
    footers:{default:new Footer({children:[new Paragraph({
      alignment:AlignmentType.CENTER,
      spacing:{before:120},
      border:{top:{style:BorderStyle.SINGLE,size:6,color:"1E5BA8",space:4}},
      children:[
        new TextRun({text:`HAP 私有部署 · ${DOCNAME}  |  第 `,color:"6B6B6B",size:18}),
        new TextRun({children:[PageNumber.CURRENT],color:"6B6B6B",size:18}),
        new TextRun({text:" 页 / 共 ",color:"6B6B6B",size:18}),
        new TextRun({children:[PageNumber.TOTAL_PAGES],color:"6B6B6B",size:18}),
        new TextRun({text:" 页",color:"6B6B6B",size:18}),
      ]})]})},
    children
  }]
});

Packer.toBuffer(doc).then(buf=>{ fs.writeFileSync(OUT,buf); console.log("written",OUT,buf.length); });
