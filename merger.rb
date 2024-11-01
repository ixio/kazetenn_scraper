# Usage : ruby merger.rb PDF_FOLDER FILENAME

# Mix order based on 2015-02-13 and 2024-02-13
TITLE_ORDER = <<TITLES.split("\n").map(&:strip)
  1
  2
  3
  4
  5
  6
  7
  8
  9
  Brest Rédaction
  Brest
  La Métropole
  Pays d’Iroise
  Pays des Abers
  Landerneau
  Pays de Landerneau
  Lesneven
  Landivisiau
  Pays de Landivisiau
  Morlaix
  Pays de Morlaix
  Pays de Saint-Pol-de-Léon
  Carhaix
  Centre-Bretagne
  Emploi
  Judiciaires
  Obsèques
  Hippisme
  Sports
  La Bourse
  Agriculture
  Marine
  Santé
  Jeux
  Vie quotidienne
  Cultures
TITLES

def page_title(file)
  header = `pdftotext -W 941 -H 50 #{file} -`.gsub(/\s+/, ' ').strip
  page_number = header.scan(/^\d\s|\s\d$/).first
  return page_number.strip if page_number

  header.split('Ouest-France').first&.strip || ''
end

def order(file1, file2)
  title1 = TITLE_ORDER.find_index{ |title_start| page_title(file1).start_with? title_start } || 100
  title2 = TITLE_ORDER.find_index{ |title_start| page_title(file2).start_with? title_start } || 100
  title1 < title2 ? [file1, file2] : [file2, file1]
end

def generate_ordered_pdf(files, filename)
  reordered_files = [files[0]] + files[1..].each_slice(2).flat_map do |file1, file2|
    file2.nil? ? file1 : order(file1, file2)
  end

  `pdftk #{reordered_files.join(' ')} output #{filename}`
end

def main(pdf_folder, filename)
  files = `ls #{pdf_folder}/*.pdf`.split.sort
  generate_ordered_pdf(files, filename)
  if File.exist?(filename) && File.size(filename) > 1_000_000 # quick&simple proxy for success
    `rm -r #{pdf_folder}`
  else
    File.write('meger.log', "#{Time.now.to_s}: Failed to create #{filename} from #{pdf_folder}\n", mode: 'a+')
  end
end

raise ArgumentError if ARGV.size != 2
main(*ARGV)
