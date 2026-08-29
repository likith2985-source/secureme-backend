const ExcelJS = require('exceljs');
const path = require('path');
const fs = require('fs');

async function compile() {
  const masterWb = new ExcelJS.Workbook();
  const masterWs = masterWb.addWorksheet('Master Report');
  
  masterWs.columns = [
    { header: 'Suite', key: 'suite', width: 20 },
    { header: 'ID', key: 'id', width: 10 },
    { header: 'Category', key: 'category', width: 20 },
    { header: 'Name', key: 'name', width: 60 },
    { header: 'Status', key: 'status', width: 10 },
    { header: 'Duration', key: 'duration', width: 12 },
  ];

  const files = [
    'appium-mobile-report.xlsx',
    'selenium-web-report.xlsx',
    'unit-test-report.xlsx',
    'validation-test-report.xlsx',
    'deployment-test-report.xlsx',
    'load-test-report.xlsx'
  ];

  for (const file of files) {
    const filePath = path.resolve(__dirname, '..', file);
    if (fs.existsSync(filePath)) {
      console.log(`Merging ${file}...`);
      const wb = new ExcelJS.Workbook();
      await wb.xlsx.readFile(filePath);
      const ws = wb.getWorksheet(1);
      
      ws.eachRow((row, rowNumber) => {
        if (rowNumber === 1) return; // skip header
        masterWs.addRow({
          suite: file.replace('.xlsx', ''),
          id: row.getCell(1).value,
          category: row.getCell(2).value,
          name: row.getCell(3).value,
          status: row.getCell(4).value,
          duration: row.getCell(5).value,
        });
      });
    }
  }

  const outPath = path.resolve(__dirname, '..', 'full-e2e-report.xlsx');
  await masterWb.xlsx.writeFile(outPath);
  console.log(`\\n✅ Master E2E report compiled to ${outPath}`);
}

compile().catch(console.error);
