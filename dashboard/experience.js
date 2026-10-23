/* User education and status reading; never changes scientific data or gates. */
const ORBIT_TERMS = [
 ['oos','OOS · Kiểm tra ngoài mẫu','out of sample oss ngoài mẫu dự báo tương lai','Kiểm tra dự báo trên dữ liệu không dùng để huấn luyện mô hình. Với nhánh theo dõi thật, dự báo phải được ghi trước khi kết quả xảy ra.','Một mô hình được chốt hôm nay, ghi dự báo cho ngày mai, rồi đợi giá thực tế để đối chiếu.'],
 ['pseudo-oos','OOS lịch sử · Historical pseudo-OOS','historical backtest replay phát lại kiểm thử quá khứ','Mô phỏng các lần dự báo trong quá khứ, mỗi lần chỉ huấn luyện bằng giai đoạn trước đó. Khi dữ liệu lịch sử đã được xem trong quá trình phát triển, kết quả này chưa phải bằng chứng độc lập về tương lai.','Mô hình dùng dữ liệu trước 2024 để kiểm tra dự báo trong năm 2024; dashboard phát lại các dự báo đã lưu.'],
 ['shock','Cú sốc · Shock','shock cú shock cú sốc biến động vĩ mô thay đổi kinh tế','Một thay đổi kinh tế có quy mô xác định để xem crypto thường phản ứng thế nào trong mẫu nghiên cứu. Không phải mọi shock trong dashboard đều là tác động nhân quả đã được nhận dạng.','Chọn VIX +5 điểm: đọc phản ứng ước lượng khi thước đo lo ngại của thị trường tăng 5 điểm.'],
 ['vix','VIX · Chỉ số biến động kỳ vọng','vix sợ hãi lo ngại chứng khoán','Thước đo biến động kỳ vọng của chỉ số S&P 500 được suy ra từ giá quyền chọn. VIX cao thường gắn với mức bất định thị trường cao hơn.','VIX từ 15 lên 20 là tăng 5 điểm, khác với tăng 5%.'],
 ['fomc','FOMC · Ủy ban chính sách tiền tệ Mỹ','fomc họp fed tiền tệ','Ủy ban của Fed đưa ra các quyết định chính sách tiền tệ Mỹ. Thông báo và họp báo có thể mang cả tin về chính sách lẫn triển vọng kinh tế.','Một tin lãi suất đi kèm đánh giá kinh tế có thể chứa hai loại thông tin khác nhau.'],
 ['fed','Fed · Ngân hàng trung ương Mỹ','fed federal reserve dự trữ liên bang','Hệ thống Dự trữ Liên bang Mỹ, thực hiện chính sách tiền tệ và nhiều chức năng ngân hàng trung ương.','Trong mục FOMC, bạn xem phản ứng giá quanh thông tin chính sách từ Fed.'],
 ['btc','BTC · Bitcoin','btc bitcoin tiền mã hóa','Ký hiệu của Bitcoin. Trong nhánh nghiên cứu daily, giá được đo bằng USD từ nguồn tổng hợp; không đồng nhất với giá BTC/USDT tại một sàn.','Chọn Bitcoin để các kết quả bên dưới dùng mẫu của BTC.'],
 ['eth','ETH · Ethereum','eth ethereum ether','Ký hiệu của Ether, tài sản gốc của mạng Ethereum. Mẫu lịch sử có thể khác Bitcoin do thời điểm bắt đầu dữ liệu.','Đổi BTC sang ETH để so sánh phản ứng của hai tài sản với cùng một thay đổi kinh tế.'],
 ['horizon','Thời hạn phản ứng · Horizon','horizon thời hạn bao lâu số ngày ngày lịch phiên','Số ngày hoặc số phiên theo dõi sau một thay đổi. Local Projections dùng ngày lịch; VAR trong dashboard dùng phiên đủ điều kiện của thị trường Mỹ.','7 ngày lịch bao gồm cuối tuần; 7 phiên không có cùng độ dài thời gian.'],
 ['regime','Trạng thái thị trường · Regime','regime calm stress full bình thường căng thẳng toàn mẫu','Cách phân loại quan sát để so sánh phản ứng trong các trạng thái như bình thường hoặc căng thẳng, theo quy tắc nghiên cứu đã định.','Mẫu căng thẳng ít quan sát hơn có thể cho khoảng tin cậy rộng hơn.'],
 ['ci','Khoảng tin cậy 95% · CI','ci confidence interval khoảng tin cậy dải màu sai số độ chắc chắn','Khoảng ước lượng thể hiện mức bất định theo phương pháp thống kê đã dùng. Nếu khoảng chứa 0, riêng khoảng này chưa cho thấy phản ứng khác 0 rõ ràng ở mức tương ứng.','Ước lượng −0,2% nhưng khoảng từ −1,2% đến +0,8%: cả tăng và giảm vẫn nằm trong khoảng. Không đọc −0,2% như dự báo chắc chắn.'],
 ['bps','Điểm cơ bản · bps','bps basis point điểm cơ bản lãi suất','Đơn vị đo chênh lệch lãi suất: 100 bps bằng 1 điểm phần trăm; 10 bps bằng 0,1 điểm phần trăm.','Lợi suất từ 4,0% lên 4,1% là tăng 10 bps.'],
 ['return','Lợi suất · Return','return lợi suất tăng giảm giá lợi nhuận log return','Mức thay đổi của giá theo thời gian. Nghiên cứu dùng log return; phần đường phản ứng hiển thị theo phần trăm và giữ đúng cách tính đã chốt.','Số âm cho biết phản ứng giảm trong mẫu; không tự bao gồm phí giao dịch hoặc cổ tức.'],
 ['lp','Local Projections · Ước lượng theo từng thời hạn','lp local projections phản ứng ước lượng','Phương pháp ước lượng phản ứng tại từng thời hạn riêng. Đường 1–30 ngày kết nối các ước lượng đó, cùng khoảng tin cậy tại mỗi điểm.','Điểm tại ngày 7 là ước lượng cho thời hạn 7 ngày, không phải giá Bitcoin dự báo ngày thứ 7.'],
 ['rolling','Rolling beta · Độ nhạy theo cửa sổ trượt','rolling beta 252 cửa sổ trượt độ nhạy','Ước lượng lặp trên các đoạn dữ liệu chuyển dần theo thời gian để xem độ nhạy thay đổi thế nào. Dashboard dùng cửa sổ 252 phiên và bước 21 phiên.','Đường beta khác nhau giữa các năm cho thấy mối liên hệ trong mẫu thay đổi theo thời gian.'],
 ['var','VAR · Mô hình tự hồi quy vector','var vector autoregression tự hồi quy vector','Mô hình mô tả nhiều chuỗi thời gian cùng lúc bằng các giá trị trễ của chúng. Phản ứng phụ thuộc cách đặt mô hình và thứ tự nhận dạng.','Mục phân tích sâu dùng hệ chung BTC–ETH; đây không phải VaR (Value at Risk).'],
 ['irf','IRF · Hàm phản ứng xung','irf impulse response phản ứng xung','Đường mô tả phản ứng theo thời gian sau một cú sốc trong mô hình VAR, dưới các giả định nhận dạng đã chọn.','Đổi thứ tự các biến có thể làm thay đổi đường IRF; nên xem cùng chẩn đoán mô hình.'],
 ['quantile','Phân vị · Quantile','quantile phân vị 5 50 95 phần trăm','Vị trí trong phân phối dữ liệu. Phân vị 5% tập trung vào vùng thấp, 50% ở giữa và 95% ở vùng cao của phân phối có điều kiện.','Phản ứng ở phân vị 5% có thể khác phản ứng tại trung vị 50%.'],
 ['rv','Realized variance · Phương sai từ giá trong ngày','rv realized variance har har-x biến động trong ngày','Thước đo được xây từ các biến động giá ở tần suất cao trong ngày. Nhánh RV dùng dữ liệu Binance USDT riêng, khác nhánh daily USD.','Lấy nến 5 phút hoặc 15 phút để dựng thước đo biến động; không ghép ngầm hai nguồn giá.'],
 ['benchmark','Benchmark · Mốc so sánh','benchmark mốc đối chứng mô hình cơ sở','Một cách dự báo làm mốc để đánh giá liệu mô hình phức tạp hơn có hữu ích hơn hay không.','Mô hình dùng thêm nhiều biến cần được so với mốc đơn giản trên cùng các ngày.'],
 ['ablation','Ablation · Kiểm tra đóng góp của nhóm biến','ablation thêm bỏ biến macro đóng góp','So sánh hai cấu hình có và không có một nhóm thông tin, giữ cách so sánh nhất quán để xem nhóm đó có cải thiện kết quả hay không.','So mô hình chỉ dùng crypto với mô hình có thêm dữ liệu kinh tế.'],
 ['mse','MSE · Sai số bình phương trung bình','mse mean squared error sai số loss','Bình quân bình phương chênh lệch giữa dự báo và kết quả thực tế. Với cùng mục tiêu và cùng mẫu, giá trị thấp hơn là sai số nhỏ hơn.','Không so MSE của lợi suất trực tiếp với QLIKE của phương sai vì hai thước đo khác nhau.'],
 ['qlike','QLIKE · Thước đo sai số dự báo biến động','qlike loss phương sai','Hàm mất mát dùng để đánh giá dự báo phương sai. So trên cùng dữ liệu, thấp hơn là tốt hơn; giá trị có thể âm.','QLIKE −6,5 có thể tốt hơn −6,4. Số âm ở đây không có nghĩa là lỗ tiền.'],
 ['pvalue','p-value · Mức bằng chứng thống kê','p p-value ý nghĩa thống kê kiểm định','Thước đo mức tương thích của dữ liệu với giả thuyết kiểm định và các giả định của mô hình. Không phải xác suất mô hình đúng hoặc dự báo sẽ thắng.','Khi kiểm tra nhiều giả thuyết, cần xem thêm hiệu chỉnh nhiều kiểm định, không chỉ p < 0,05.'],
 ['bh','BH q · Hiệu chỉnh nhiều kiểm định','bh q q-value benjamini hochberg nhiều kiểm định','Giá trị p đã được điều chỉnh theo phương pháp Benjamini–Hochberg trong từng nhóm kiểm định quy định trước, nhằm kiểm soát tỷ lệ phát hiện sai kỳ vọng.','Một kết quả có p nhỏ nhưng q lớn có thể không còn đạt ngưỡng sau hiệu chỉnh.'],
 ['pit','PIT · Thông tin đúng thời điểm','pit point in time rò rỉ dữ liệu leakage','Chỉ dùng thông tin thực sự được coi là khả dụng tại lúc dự báo. Ngày quan sát của một số liệu có thể sớm hơn ngày công bố hoặc ngày nhận được.','GDP quý trước được công bố hôm nay không thể dùng như thông tin đã biết từ đầu quý trước.'],
 ['vintage','Vintage · Phiên bản dữ liệu','vintage sửa đổi revision alfred phiên bản dữ liệu','Bản dữ liệu mà nguồn cung cấp tại một thời điểm. Một số chỉ tiêu kinh tế có thể được sửa lại sau công bố ban đầu.','Dữ liệu mới nhất tải hôm nay có thể khác dữ liệu mà người dự báo đã nhìn thấy năm trước.'],
 ['cutoff','Cutoff · Hạn chốt thông tin','cutoff receipt thời điểm nhận hạn chót buffer','Mốc muộn nhất mà thông tin được phép đi vào một dự báo. Receipt ghi thời điểm thực sự nhận dữ liệu; tải muộn không được đổi thành nhận sớm.','Nguồn về sau hạn chốt khiến ngày đó không đủ điều kiện; hệ thống không dựng bù dự báo cũ.'],
 ['target','Mục tiêu dự báo · Target','target label nhãn mục tiêu','Đại lượng mà mô hình cần dự báo; nhãn là kết quả thực tế để đối chiếu sau đó.','Chọn lợi suất mỗi ngày hoặc mức biến động giá; hai mục tiêu dùng cách đánh giá khác nhau.'],
 ['elastic','Elastic Net','elastic net hồi quy regularization thuật toán','Mô hình hồi quy có cơ chế điều chuẩn để hạn chế hệ số quá lớn và xử lý nhiều biến giải thích. Tên thuật toán không tự nói lên chất lượng dự báo.','So sánh kết quả ngoài mẫu với mô hình làm mốc thay vì chỉ nhìn độ khớp trên mẫu huấn luyện.'],
 ['boosting','Gradient boosting','boosting histogram cây mô hình machine learning','Phương pháp học máy kết hợp nhiều mô hình cây theo từng bước để cải thiện mục tiêu tối ưu. Vẫn cần kiểm tra ngoài mẫu và giới hạn thông tin đúng thời điểm.','Mô hình phức tạp hơn có thể khớp dữ liệu cũ tốt nhưng không nhất thiết dự báo tương lai tốt hơn.'],
];
function orbitNormalize(s){return String(s).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/[^a-z0-9]+/g,' ').trim();}
function orbitSearchTerms(query){
 const words=orbitNormalize(query).split(/\s+/).filter(Boolean);
 return ORBIT_TERMS.map(t=>({term:t,text:orbitNormalize(t.slice(0,4).join(' '))})).filter(t=>words.every(w=>w.length<=3?t.text.split(/[^a-z0-9]+/).includes(w):t.text.includes(w))).sort((a,b)=>Number(orbitNormalize(b.term[1]).startsWith(orbitNormalize(query)))-Number(orbitNormalize(a.term[1]).startsWith(orbitNormalize(query)))).map(r=>r.term);
}
(() => {
 if(typeof window==='undefined'||!document.documentElement)return;
 const $=id=>document.getElementById(id), root=document.documentElement;
 const text=(id,value)=>{const e=$(id);if(e)e.textContent=value;};
 const workspaceRenderer=showWorkspace;
 showWorkspace=function(view){workspaceRenderer(view);$('mobileWorkspace').value=root.dataset.workspace||view;};
 $('mobileWorkspace').value=root.dataset.workspace||initialWorkspace;
 $('mobileWorkspace').addEventListener('change',e=>{showWorkspace(e.target.value);window.scrollTo({top:0,behavior:'instant'});});
 window.addEventListener('hashchange',()=>{$('mobileWorkspace').value=root.dataset.workspace;});
 const date=value=>{const d=new Date(value);return !value||Number.isNaN(d.getTime())?'Chưa có thông tin':d.toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});};
 let lastFocus=null, selectedTerm=null, commandRows=[], commandIndex=0;
 const commandActions=()=>[
  ...Object.entries(WORKSPACE_NAMES).map(([key,label])=>({key:'go-'+key,title:'Mở '+label,aliases:key+' workspace chuyển trang',group:'Đi đến',run:()=>{showWorkspace(key);window.scrollTo({top:0,behavior:'instant'});}})),
  {key:'theme',title:'Đổi giao diện sáng / tối',aliases:'theme dark light giao dien',group:'Thao tác',run:()=>window.orbitToggleTheme()},
  {key:'csv',title:'Tải CSV của workspace',aliases:'export download tai xuat du lieu',group:'Thao tác',run:()=>window.orbitExportCurrent()},
  {key:'print',title:'In workspace đang xem',aliases:'print ban in pdf',group:'Thao tác',run:()=>window.print()},
  {key:'keys',title:'Xem phím tắt',aliases:'shortcut keyboard ban phim',group:'Thao tác',run:()=>$('shortcutDialog').showModal()},
 ];
 function highlight(label,query){
  const span=document.createElement('span'),normal=orbitNormalize(label),word=orbitNormalize(query).split(' ').find(w=>w&&normal.includes(w));
  if(!word){span.textContent=label;return span;}
  // Vietnamese precomposed characters map one-to-one after removing accents.
  const start=normal.indexOf(word),before=document.createTextNode(label.slice(0,start)),mark=document.createElement('mark');mark.textContent=label.slice(start,start+word.length);span.append(before,mark,document.createTextNode(label.slice(start+word.length)));return span;
 }
 function selectTerm(term){
  selectedTerm=term[0];const box=$('glossaryDetail');box.replaceChildren();
  const title=document.createElement('h3');title.textContent=term[1];
  const body=document.createElement('p');body.textContent=term[3];
  const example=document.createElement('div');example.className='term-example';
  const label=document.createElement('strong');label.textContent='Ví dụ';
  const para=document.createElement('p');para.textContent=term[4];example.append(label,para);
  const link=document.createElement('a');link.href='https://www.google.com/search?q='+encodeURIComponent(term[1]+' finance giải thích');link.target='_blank';link.rel='noopener noreferrer';link.textContent='Tìm hiểu thêm trên Google ↗';
  box.append(title,body,example,link);
 }
 function focusCommand(index){
  commandIndex=Math.max(0,Math.min(commandRows.length-1,index));
  const row=commandRows[commandIndex];if(!row)return;
  const buttons=[...$('glossaryResults').querySelectorAll('button')];buttons.forEach((b,i)=>b.setAttribute('aria-selected',String(i===commandIndex)));
  if(buttons[commandIndex]){buttons[commandIndex].scrollIntoView({block:'nearest'});$('glossarySearch').setAttribute('aria-activedescendant',buttons[commandIndex].id);}
  if(row.term)selectTerm(row.term);else{const box=$('glossaryDetail');box.replaceChildren();const h=document.createElement('h3');h.textContent=row.title;const p=document.createElement('p');p.textContent='Nhấn Enter hoặc chọn kết quả để thực hiện.';box.append(h,p);}
 }
 function activateCommand(index){const row=commandRows[index];if(!row)return;if(row.term){focusCommand(index);return;}$('glossaryDialog').close();row.run();}
 function searchTerms(){
  const query=$('glossarySearch').value,words=orbitNormalize(query).split(' ').filter(Boolean),list=$('glossaryResults');list.replaceChildren();
  const actions=commandActions().filter(a=>words.every(w=>orbitNormalize(a.title+' '+a.aliases).includes(w)));
  const terms=orbitSearchTerms(query).slice(0,query?16:6).map(term=>({key:term[0],title:term[1],group:'Thuật ngữ',term}));
  commandRows=[...actions,...terms];commandIndex=0;
  if(!commandRows.length){const p=document.createElement('p');p.textContent='Chưa có kết quả. Thử từ ngắn hơn.';list.append(p);const link=document.createElement('a');link.href='https://www.google.com/search?q='+encodeURIComponent(query+' tài chính crypto');link.target='_blank';link.rel='noopener noreferrer';link.textContent='Tìm trên Google ↗';list.append(link);$('glossaryDetail').replaceChildren();return;}
  let group='';commandRows.forEach((row,i)=>{if(row.group!==group){group=row.group;const label=document.createElement('div');label.className='command-group';label.textContent=group;list.append(label);}const b=document.createElement('button');b.type='button';b.id='command-result-'+i;b.dataset.key=row.key;b.append(highlight(row.title,query));b.setAttribute('role','option');b.setAttribute('aria-selected','false');b.addEventListener('click',()=>activateCommand(i));b.addEventListener('pointerenter',()=>focusCommand(i));list.append(b);});
  const remembered=commandRows.findIndex(r=>r.term&&r.term[0]===selectedTerm);focusCommand(query&&remembered>=0?remembered:0);
 }
 function openGlossary(key){
  lastFocus=document.activeElement;const term=ORBIT_TERMS.find(t=>t[0]===key);if(term)selectedTerm=term[0];else selectedTerm=null;
  $('glossarySearch').value=term?term[1].split(' · ')[0]:'';if(!$('glossaryDialog').open)$('glossaryDialog').showModal();$('glossarySearch').setAttribute('aria-expanded','true');searchTerms();$('glossarySearch').focus();$('glossarySearch').select();
 }
 window.orbitOpenCommand=openGlossary;
 $('openGlossary').addEventListener('click',()=>openGlossary());$('closeGlossary').addEventListener('click',()=>$('glossaryDialog').close());
 $('glossaryDialog').addEventListener('close',()=>{$('glossarySearch').setAttribute('aria-expanded','false');if(lastFocus&&lastFocus.isConnected)lastFocus.focus();});
 $('glossaryDialog').addEventListener('click',e=>{const r=e.currentTarget.getBoundingClientRect();if(e.target===e.currentTarget&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))e.currentTarget.close();});
 $('glossarySearch').addEventListener('input',searchTerms);
 $('glossarySearch').addEventListener('keydown',e=>{if(e.key==='ArrowDown'){e.preventDefault();focusCommand(commandIndex+1);}if(e.key==='ArrowUp'){e.preventDefault();focusCommand(commandIndex-1);}if(e.key==='Enter'){e.preventDefault();activateCommand(commandIndex);}});
 document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openGlossary();}});
 document.addEventListener('click',e=>{const b=e.target.closest('[data-term]');if(b)openGlossary(b.dataset.term);});
 const readingNumber=new Intl.NumberFormat('vi-VN',{minimumFractionDigits:3,maximumFractionDigits:3});
 function updateResponseReading(){
  const row=responseRows().find(r=>r.horizon_days===Number($('horizon').value));if(!row)return;
  const n=v=>readingNumber.format(Number(v)),shock=$('shock').selectedOptions[0].textContent;
  text('responseReadingTitle',`${shock} → ${row.asset.toUpperCase()} ước lượng ${row.beta_pct>0?'+':''}${n(row.beta_pct)}% sau ${row.horizon_days} ngày.`);
  text('responseReadingBody',`CI 95%: ${n(row.lower95)}% đến ${n(row.upper95)}%. Kết quả ước lượng từ lịch sử.`);
 }
 const responseRenderer=renderResponse;
 renderResponse=function(){const start=performance.now();responseRenderer();updateResponseReading();root.dataset.responseRenderMs=(performance.now()-start).toFixed(1);};
 let responseFrame=null;
 const queuedResponse=()=>{if(responseFrame!==null)cancelAnimationFrame(responseFrame);responseFrame=requestAnimationFrame(()=>{responseFrame=null;renderResponse();});};
 for(const id of ['asset','shock','regime','horizon']){$(id).removeEventListener('change',responseRenderer);$(id).addEventListener('change',queuedResponse);}
 function updateForecastReading(){
  const s=selectedForecast(),pair=historyPairs[Number($('forecastPair').value||0)],row=LATEST.ablation.find(r=>matches(r,s)&&r.base===pair[0]&&r.added===pair[1]);if(!row)return;
  const better=row.mean_loss_new_minus_base<0,significant=row.qvalue_bh!==null&&row.qvalue_bh<.05;
  text('forecastReadingTitle',`Thêm dữ liệu: sai số ${better?'thấp hơn':'cao hơn'} trong kỳ đang chọn.`);
  text('forecastReadingBody',`${significant?'Đạt':'Chưa đạt'} BH q < 0,05 · ${row.n.toLocaleString('vi-VN')} ngày ghép cặp. Historical pseudo-OOS / exploratory.${s.scenario==='matched_latest_d3'?' Dữ liệu sửa sau: chỉ để đối chiếu.':''}`);
 }
 window.orbitUpdateForecast=updateForecastReading;
 const forecastRenderer=renderForecast;
 renderForecast=function(){forecastRenderer();updateForecastReading();};
 for(const id of ['target','forecastModel','forecastPair','fAsset','fScenario']){$(id).removeEventListener('change',forecastRenderer);$(id).addEventListener('change',renderForecast);}
 $('retryHistory').addEventListener('click',()=>loadForecastWorkspace());
 for(const b of document.querySelectorAll('[data-example]'))b.addEventListener('click',()=>{
  const examples={vix:{asset:'btc',shock:'vix_change',horizon:'7'},usd:{asset:'eth',shock:'usd_return_pct',horizon:'7'},fomc:{asset:'btc',shock:'monetary',horizon:'3'}};
  for(const [key,value]of Object.entries(examples[b.dataset.example]))$(key).value=value;
  $('regime').value='full';showWorkspace('transmission');renderResponse();$('responses').scrollIntoView({block:'start',behavior:'smooth'});
 });
 // Reports may contain machine vocabulary; explain it beside the results.
 const terms={asset:'btc',shock:'shock',regime:'regime',horizon:'horizon',target:'target',forecastModel:'elastic',fScenario:'pit',forecastPair:'ablation',varOrder:'irf',rvSampling:'rv',eOutcome:'fomc'};
 for(const [id,key] of Object.entries(terms)){const select=$(id),label=select&&select.closest('label');if(!label||label.querySelector('[data-term]'))continue;const h=document.createElement('button');h.type='button';h.className='term-help';h.dataset.term=key;h.setAttribute('aria-label','Giải thích '+label.childNodes[0].textContent.trim());h.textContent='?';label.append(h);}
 for(const option of $('horizon').options)option.textContent=option.value+' ngày';
 const cutoff=document.querySelector('.topbar-date');if(cutoff)cutoff.title='Mẫu ước lượng nghiên cứu được giữ cố định. Dữ liệu đầu vào và dự báo mới cập nhật theo lịch ở Dữ liệu & OOS.';
 let status=ORBIT_STATUS;
 let liveDataRendered=null;
 function renderLiveData(){
  if(root.dataset.workspace!=='operations'||liveDataRendered===status)return;
  liveDataRendered=status;
  const observations=status.capture?.observations||[],forecasts=status.latest_forecasts||[];
  $('liveObservationTable').innerHTML=observations.length?table(['Biến','Giá trị','Đơn vị','Ngày quan sát','Vintage','Nhận lúc (VN)','Nguồn'],observations.map(r=>[r.label,r.value,r.unit,r.observation_date,r.vintage_date||'—',date(r.received_at_utc),r.source])):'<p>Chưa có quan sát đã xác minh trong bản này.</p>';
  $('liveForecastTable').innerHTML=forecasts.length?table(['Tài sản','Dự báo r²','Mô hình','Origin UTC','Cấu hình','Ngày thông tin','Ghi lúc (VN)'],forecasts.map(r=>[r.asset,r.predicted_squared_return.toPrecision(7),r.model,r.origin_utc,typeof humanVariant==='function'?humanVariant(r.variant):r.variant,r.information_day,date(r.logged_at_utc)])):'<p>Chưa có dự báo đủ điều kiện được ghi; không tạo bù.</p>';
  text('liveForecastContext',`Mẫu ước lượng biểu đồ: ${status.research_cutoff}. Đang hiển thị ${forecasts.length} dự báo rủi ro học máy mới nhất theo từng tài sản. Dữ liệu mới không tự thay LP/VAR/FOMC hoặc huấn luyện lại mô hình.`);
  $('exportLiveForecast').disabled=!forecasts.length;
 }
 window.orbitRenderLiveData=renderLiveData;
 $('exportLiveForecast').addEventListener('click',()=>window.orbitExportLiveForecast?.());
 const shortCaptureDate=new Intl.DateTimeFormat('vi-VN',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Ho_Chi_Minh'});
 function showStatus(data,source){
  status=data;window.orbitStatus=data;const worker=data.worker||{},p=data.prospective||{},last=Date.parse(worker.last_success_utc),age=Number.isFinite(last)?Date.now()-last:Infinity,stale=age>(data.schedule?.stale_after_minutes||150)*60000;
  const enabled=worker.installed===true,health=worker.health_status==='healthy';
  text('statusBadge',!enabled?'Chưa xác minh lịch chạy':stale?'Trạng thái quá 150 phút':health?'Worker hoạt động tại lần kiểm tra':'Cần kiểm tra worker');
  $('statusBadge').dataset.state=enabled&&health&&!stale?'good':'warning';
  text('statusLastRun',date(worker.last_success_utc));
  text('statusWorkerDetail',`${worker.provider==='github-actions'?'GitHub Actions.':'Nơi chạy: '+(worker.provider||'chưa xác minh')+'.'} ${stale?'Thông tin đã cũ; đối chiếu lịch sử chạy.':'Thời điểm theo metadata công khai.'}`);
  text('statusPredictions',`${p.prediction_files??0} tệp · ${p.prediction_rows??0} dòng dự báo`);
  text('statusPredictionDetail',`${p.label_files??0} tệp nhãn thực tế. ${p.prediction_rows?'Đợi đủ nhãn và đến kỳ đánh giá.':'Bản này chưa ghi dự báo mới đủ điều kiện.'}`);
  text('statusEvaluation',p.fixed_end?new Date(p.fixed_end).toLocaleDateString('vi-VN',{timeZone:'UTC'})+' · UTC':'Chưa có thông tin');
  text('statusEvaluationDetail',p.performance==='PENDING_FIXED_EVALUATION_WINDOW'?'Chưa đến kỳ đánh giá cố định. Dashboard chưa xác nhận năng lực dự báo tương lai.':'Trạng thái đánh giá: '+(p.performance||'chưa có thông tin')+'.');
  const capture=data.capture||{};
  text('latestDataBadge',capture.status==='verified'?'Thu mới: '+shortCaptureDate.format(new Date(capture.finished_at_utc)):'Thu mới: chưa xác minh');
  if(cutoff&&capture.status==='verified')cutoff.title=`Mẫu ước lượng: ${data.research_cutoff}. Capture nhận lúc ${date(capture.finished_at_utc)} (VN), ${capture.sources_ok}/${capture.sources_total} nguồn; ngày quan sát nằm ở bảng Dữ liệu & OOS.`;
  text('statusCaptureTime',capture.status==='verified'?date(capture.finished_at_utc):'Chưa có biên bản thu trong bản này');
  text('statusCaptureSources',capture.status==='verified'?`${capture.sources_ok}/${capture.sources_total} nguồn thành công; đã đối chiếu hash biên bản thu.`:'Bản này chưa có biên bản thu dữ liệu đã xác minh.');
  text('statusMessage',`${source} · ${date(data.generated_at_utc)} giờ Việt Nam. Chỉ đọc metadata.`);
  renderLiveData();
 }
 let checking=false;
 async function checkStatus(){
  if(checking)return;checking=true;$('refreshStatus').disabled=true;text('statusMessage','Đang đọc metadata công khai của website…');
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),6000);
  try{
   const url=location.protocol==='file:'?'https://tranthanhphu39.github.io/dashboard_crypto/dashboard/status.json':new URL('status.json',location.href).href;
   const response=await fetch(url,{cache:'no-store',signal:controller.signal});if(!response.ok)throw new Error('Trạng thái chưa được xuất bản (HTTP '+response.status+').');
   const next=await response.json();if(next.schema_version!==1||next.repository!=='TranThanhPhu39/dashboard_crypto')throw new Error('Định dạng trạng thái không phù hợp.');
   showStatus(next,'Đã kiểm tra website');
   if(next.generated_at_utc!==ORBIT_STATUS.generated_at_utc){const a=document.createElement('a');a.href='https://tranthanhphu39.github.io/dashboard_crypto/dashboard/';a.target='_blank';a.rel='noopener noreferrer';a.textContent='Mở bản online mới nhất ↗';$('statusMessage').append(' ',a);}
  }catch(error){showStatus(status,'Đang dùng trạng thái nhúng trong file');text('statusMessage',$('statusMessage').textContent+' Chưa kiểm tra được website: '+(error.name==='AbortError'?'kết nối quá thời gian chờ.':error.message)+' Có thể dùng bản nhúng và đối chiếu GitHub.');}
  finally{clearTimeout(timeout);checking=false;$('refreshStatus').disabled=false;}
 }
 $('refreshStatus').addEventListener('click',checkStatus);showStatus(status,location.protocol==='file:'?'Bản HTML mở trên máy':'Trạng thái đi kèm bản website này');
 if(location.protocol==='https:'||location.protocol==='http:'){checkStatus();setInterval(()=>{if(!document.hidden)checkStatus();},300000);}
 // Restore readable labels after each render, without replacing numeric values.
 const labels={transmission:'Truyền dẫn',forecast:'Dự báo rủi ro',fomc:'FOMC',advanced:'Phân vị & VAR'};
 for(const [key,label]of Object.entries(labels)){const span=$('tab-'+key).querySelector('span');if(span)span.textContent=label;}
 updateResponseReading();
 orbitStartStudio();
 for(const node of document.querySelectorAll('[data-orbit-inert]'))node.removeAttribute('inert');
 $('bootStatus').hidden=true;
 root.dataset.orbitReady='true';
})();
