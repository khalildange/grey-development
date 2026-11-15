// Render one page of a PDF to a JPEG at a given pixel width.
//   pdfpage <in.pdf> <page (1-based)> <width px> <out.jpg> [quality 0-1]
// Uses the trim box, so a print file with bleed renders at its finished size.
// Build: swiftc -O tools/pdfpage.swift -o /tmp/pdfpage
import Foundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let a = CommandLine.arguments
guard a.count >= 5, let pageNo = Int(a[2]), let width = Int(a[3]),
      let doc = CGPDFDocument(URL(fileURLWithPath: a[1]) as CFURL),
      let page = doc.page(at: pageNo) else { FileHandle.standardError.write("usage/pdf error\n".data(using: .utf8)!); exit(1) }
let quality = a.count > 5 ? Double(a[5]) ?? 0.82 : 0.82
let box = page.getBoxRect(.trimBox)
let scale = CGFloat(width) / box.width
let h = Int((box.height * scale).rounded())
guard let ctx = CGContext(data: nil, width: width, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                          space: CGColorSpace(name: CGColorSpace.sRGB)!,
                          bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { exit(2) }
ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
ctx.fill(CGRect(x: 0, y: 0, width: width, height: h))
ctx.interpolationQuality = .high
ctx.scaleBy(x: scale, y: scale)
ctx.translateBy(x: -box.minX, y: -box.minY)
ctx.drawPDFPage(page)
guard let img = ctx.makeImage(),
      let dst = CGImageDestinationCreateWithURL(URL(fileURLWithPath: a[4]) as CFURL, UTType.jpeg.identifier as CFString, 1, nil) else { exit(3) }
CGImageDestinationAddImage(dst, img, [kCGImageDestinationLossyCompressionQuality: quality] as CFDictionary)
exit(CGImageDestinationFinalize(dst) ? 0 : 4)
