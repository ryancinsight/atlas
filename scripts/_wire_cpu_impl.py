#!/usr/bin/env python3
"""Insert 16 new PoolOps method impls into the PoolOps blanket impl block.

Reads the file as bytes, finds the AVG_POOL3D_BACKWARD closing brace `    }` followed
by the PoolOps impl-block close `}` (unique 2-line pattern at the end of the block),
and inserts all 16 new methods between them. Preserves CRLF if present.
"""
import sys

POOL_IMPL_PATH = r"coeus-ops/src/backend_ops/cpu_impl.rs"

NEW_METHODS = '''

    // ===== G-036 MS-189a 1D pool =====

    #[inline]
    fn max_pool1d(
        &self,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        kernel_size: usize,
        stride: usize,
        padding: usize,
        dilation: usize,
        output: &mut Self::DeviceBuffer<T>,
        output_layout: &Layout,
    ) {
        pool::max_pool1d(self, input, input_layout, kernel_size, stride, padding, dilation, output, output_layout);
    }

    #[inline]
    fn max_pool1d_backward(
        &self,
        grad_out: &Self::DeviceBuffer<T>,
        grad_out_layout: &Layout,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        kernel_size: usize,
        stride: usize,
        padding: usize,
        dilation: usize,
        grad_input: &mut Self::DeviceBuffer<T>,
        grad_input_layout: &Layout,
    ) {
        pool::max_pool1d_backward(
            self, grad_out, grad_out_layout, input, input_layout, kernel_size, stride, padding, dilation, grad_input, grad_input_layout,
        );
    }

    #[inline]
    fn avg_pool1d(
        &self,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        kernel_size: usize,
        stride: usize,
        padding: usize,
        dilation: usize,
        output: &mut Self::DeviceBuffer<T>,
        output_layout: &Layout,
    ) {
        pool::avg_pool1d(self, input, input_layout, kernel_size, stride, padding, dilation, output, output_layout);
    }

    #[inline]
    fn avg_pool1d_backward(
        &self,
        grad_out: &Self::DeviceBuffer<T>,
        grad_out_layout: &Layout,
        kernel_size: usize,
        stride: usize,
        padding: usize,
        dilation: usize,
        grad_input: &mut Self::DeviceBuffer<T>,
        grad_input_layout: &Layout,
    ) {
        pool::avg_pool1d_backward(
            self, grad_out, grad_out_layout, kernel_size, stride, padding, dilation, grad_input, grad_input_layout,
        );
    }

    // ===== G-036 MS-189b adaptive pool =====

    #[inline]
    fn adaptive_max_pool1d(
        &self,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        output_size: usize,
        output: &mut Self::DeviceBuffer<T>,
        output_layout: &Layout,
    ) {
        pool::adaptive_max_pool1d(self, input, input_layout, output_size, output, output_layout);
    }

    #[inline]
    fn adaptive_max_pool1d_backward(
        &self,
        grad_out: &Self::DeviceBuffer<T>,
        grad_out_layout: &Layout,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        output_size: usize,
        grad_input: &mut Self::DeviceBuffer<T>,
        grad_input_layout: &Layout,
    ) {
        pool::adaptive_max_pool1d_backward(
            self, grad_out, grad_out_layout, input, input_layout, output_size, grad_input, grad_input_layout,
        );
    }

    #[inline]
    fn adaptive_max_pool2d(
        &self,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        output_h: usize,
        output_w: usize,
        output: &mut Self::DeviceBuffer<T>,
        output_layout: &Layout,
    ) {
        pool::adaptive_max_pool2d(self, input, input_layout, output_h, output_w, output, output_layout);
    }

    #[inline]
    fn adaptive_max_pool2d_backward(
        &self,
        grad_out: &Self::DeviceBuffer<T>,
        grad_out_layout: &Layout,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        output_h: usize,
        output_w: usize,
        grad_input: &mut Self::DeviceBuffer<T>,
        grad_input_layout: &Layout,
    ) {
        pool::adaptive_max_pool2d_backward(
            self, grad_out, grad_out_layout, input, input_layout, output_h, output_w, grad_input, grad_input_layout,
        );
    }

    #[inline]
    fn adaptive_max_pool3d(
        &self,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        output_d: usize,
        output_h: usize,
        output_w: usize,
        output: &mut Self::DeviceBuffer<T>,
        output_layout: &Layout,
    ) {
        pool::adaptive_max_pool3d(self, input, input_layout, output_d, output_h, output_w, output, output_layout);
    }

    #[inline]
    fn adaptive_max_pool3d_backward(
        &self,
        grad_out: &Self::DeviceBuffer<T>,
        grad_out_layout: &Layout,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        output_d: usize,
        output_h: usize,
        output_w: usize,
        grad_input: &mut Self::DeviceBuffer<T>,
        grad_input_layout: &Layout,
    ) {
        pool::adaptive_max_pool3d_backward(
            self, grad_out, grad_out_layout, input, input_layout, output_d, output_h, output_w, grad_input, grad_input_layout,
        );
    }

    #[inline]
    fn adaptive_avg_pool1d(
        &self,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        output_size: usize,
        output: &mut Self::DeviceBuffer<T>,
        output_layout: &Layout,
    ) {
        pool::adaptive_avg_pool1d(self, input, input_layout, output_size, output, output_layout);
    }

    #[inline]
    fn adaptive_avg_pool1d_backward(
        &self,
        grad_out: &Self::DeviceBuffer<T>,
        grad_out_layout: &Layout,
        input_layout: &Layout,
        output_size: usize,
        grad_input: &mut Self::DeviceBuffer<T>,
        grad_input_layout: &Layout,
    ) {
        pool::adaptive_avg_pool1d_backward(
            self, grad_out, grad_out_layout, input_layout, output_size, grad_input, grad_input_layout,
        );
    }

    #[inline]
    fn adaptive_avg_pool2d(
        &self,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        output_h: usize,
        output_w: usize,
        output: &mut Self::DeviceBuffer<T>,
        output_layout: &Layout,
    ) {
        pool::adaptive_avg_pool2d(self, input, input_layout, output_h, output_w, output, output_layout);
    }

    #[inline]
    fn adaptive_avg_pool2d_backward(
        &self,
        grad_out: &Self::DeviceBuffer<T>,
        grad_out_layout: &Layout,
        input_layout: &Layout,
        output_h: usize,
        output_w: usize,
        grad_input: &mut Self::DeviceBuffer<T>,
        grad_input_layout: &Layout,
    ) {
        pool::adaptive_avg_pool2d_backward(
            self, grad_out, grad_out_layout, input_layout, output_h, output_w, grad_input, grad_input_layout,
        );
    }

    #[inline]
    fn adaptive_avg_pool3d(
        &self,
        input: &Self::DeviceBuffer<T>,
        input_layout: &Layout,
        output_d: usize,
        output_h: usize,
        output_w: usize,
        output: &mut Self::DeviceBuffer<T>,
        output_layout: &Layout,
    ) {
        pool::adaptive_avg_pool3d(self, input, input_layout, output_d, output_h, output_w, output, output_layout);
    }

    #[inline]
    fn adaptive_avg_pool3d_backward(
        &self,
        grad_out: &Self::DeviceBuffer<T>,
        grad_out_layout: &Layout,
        input_layout: &Layout,
        output_d: usize,
        output_h: usize,
        output_w: usize,
        grad_input: &mut Self::DeviceBuffer<T>,
        grad_input_layout: &Layout,
    ) {
        pool::adaptive_avg_pool3d_backward(
            self, grad_out, grad_out_layout, input_layout, output_d, output_h, output_w, grad_input, grad_input_layout,
        );
    }
'''


def main() -> int:
    with open(POOL_IMPL_PATH, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8")
    crlf = b"\r\n" in raw
    le = "\r\n" if crlf else "\n"
    text_lf = text.replace("\r\n", "\n")

    # Find the unique anchor: avg_pool3d_backward body close followed by PoolOps impl block close.
    # The body close is `        );` on one line and `    }` on the next, and the impl block close is `}`.
    # We use the last 12 lines of avg_pool3d_backward's body as context for uniqueness.
    anchor_lf = (
        "        );\n"
        "    }\n"
        "}\n"
        "\n"
        "#[allow(clippy::too_many_arguments)]\n"
        "impl<T: Scalar + leto_ops::Scalar, B: CpuBackend> OptimizerOps<T> for B"
    )
    count = text_lf.count(anchor_lf)
    if count != 1:
        print(f"ERROR: anchor matched {count} times; expected 1", flush=True)
        return 1

    # Insert NEW_METHODS between `    }\n` (body close) and `}\n\n#[allow...]`
    # The replacement: keep `    }\n` (body close), then NEW_METHODS, then `}` (impl close + rest)
    new_text_lf = text_lf.replace(
        anchor_lf,
        "        );\n"
        "    }\n"
        + NEW_METHODS
        + "}\n"
        "\n"
        "#[allow(clippy::too_many_arguments)]\n"
        "impl<T: Scalar + leto_ops::Scalar, B: CpuBackend> OptimizerOps<T> for B",
        1,
    )

    # Sanity
    assert "fn adaptive_max_pool3d_backward" in new_text_lf
    assert "fn max_pool1d" in new_text_lf
    assert new_text_lf.count("impl<T: Scalar + leto_ops::Scalar, B: CpuBackend> OptimizerOps<T> for B") == 1

    if crlf:
        new_bytes = new_text_lf.replace("\n", "\r\n").encode("utf-8")
    else:
        new_bytes = new_text_lf.encode("utf-8")

    with open(POOL_IMPL_PATH, "wb") as f:
        f.write(new_bytes)
    print(f"SUCCESS: cpu_impl.rs updated to {len(new_text_lf.splitlines())} lines, CRLF preserved: {crlf}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
