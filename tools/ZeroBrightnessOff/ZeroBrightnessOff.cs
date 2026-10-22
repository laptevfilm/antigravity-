using System;
using System.Management;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

namespace ZeroBrightnessOff
{
    static class Program
    {
        [DllImport("user32.dll")]
        private static extern IntPtr DefWindowProc(IntPtr hWnd, int uMsg, IntPtr wParam, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern bool SendNotifyMessage(IntPtr hWnd, int Msg, IntPtr wParam, IntPtr lParam);

        private const int WM_SYSCOMMAND = 0x0112;
        private const int SC_MONITORPOWER = 0xF170;
        private const int MONITOR_OFF = 2;

        private static Form _hiddenForm;

        [MTAThread]
        static void Main()
        {
            bool createdNew;
            using (var mutex = new Mutex(true, @"Local\AcerZeroBrightnessOffDaemon", out createdNew))
            {
                if (!createdNew)
                    return;

                var uiThread = new Thread(() =>
                {
                    _hiddenForm = new Form
                    {
                        ShowInTaskbar = false,
                        FormBorderStyle = FormBorderStyle.None,
                        WindowState = FormWindowState.Minimized,
                        Opacity = 0
                    };
                    IntPtr handle = _hiddenForm.Handle;
                    Application.Run();
                });
                uiThread.SetApartmentState(ApartmentState.STA);
                uiThread.IsBackground = true;
                uiThread.Start();

                int lastBrightness = GetCurrentBrightness();
                if (lastBrightness == 0)
                {
                    SetBrightness(1);
                    lastBrightness = 1;
                }

                long reachedMinTick = 0;
                long lastOffTick = 0;

                // Outer loop recreates WMI watcher automatically if GPU driver updates or WMI restarts
                while (true)
                {
                    try
                    {
                        var scope = new ManagementScope(@"\\.\root\WMI");
                        var query = new WqlEventQuery("SELECT * FROM WmiMonitorBrightnessEvent");

                        using (var watcher = new ManagementEventWatcher(scope, query))
                        {
                            watcher.Start();
                            while (true)
                            {
                                ManagementBaseObject ev = watcher.WaitForNextEvent();
                                int current = Convert.ToInt32(ev["Brightness"]);
                                long now = Environment.TickCount;

                                if (current == 0)
                                {
                                    int prev = lastBrightness;

                                    SetBrightness(1);
                                    lastBrightness = 1;

                                    if (prev > 1)
                                    {
                                        reachedMinTick = now;
                                        continue;
                                    }

                                    if (unchecked(now - reachedMinTick) < 250 || unchecked(now - lastOffTick) < 1200)
                                        continue;

                                    lastOffTick = now;

                                    ThreadPool.QueueUserWorkItem(_ =>
                                    {
                                        Thread.Sleep(400);
                                        TurnOffMonitor();
                                    });
                                }
                                else
                                {
                                    lastBrightness = current;
                                }
                            }
                        }
                    }
                    catch
                    {
                        Thread.Sleep(2000);
                    }
                }
            }
        }

        private static void TurnOffMonitor()
        {
            try
            {
                if (_hiddenForm != null && _hiddenForm.IsHandleCreated)
                {
                    _hiddenForm.BeginInvoke(new Action(() =>
                    {
                        DefWindowProc(_hiddenForm.Handle, WM_SYSCOMMAND, (IntPtr)SC_MONITORPOWER, (IntPtr)MONITOR_OFF);
                    }));
                }
                SendNotifyMessage((IntPtr)0xFFFF, WM_SYSCOMMAND, (IntPtr)SC_MONITORPOWER, (IntPtr)MONITOR_OFF);
            }
            catch { }
        }

        private static int GetCurrentBrightness()
        {
            try
            {
                using (var searcher = new ManagementObjectSearcher(@"\\.\root\WMI", "SELECT CurrentBrightness FROM WmiMonitorBrightness"))
                {
                    foreach (ManagementObject obj in searcher.Get())
                    {
                        return Convert.ToInt32(obj["CurrentBrightness"]);
                    }
                }
            }
            catch { }
            return 10;
        }

        private static void SetBrightness(byte target)
        {
            try
            {
                using (var searcher = new ManagementObjectSearcher(@"\\.\root\WMI", "SELECT * FROM WmiMonitorBrightnessMethods"))
                {
                    foreach (ManagementObject obj in searcher.Get())
                    {
                        using (ManagementBaseObject inParams = obj.GetMethodParameters("WmiSetBrightness"))
                        {
                            inParams["Timeout"] = (uint)0;
                            inParams["Brightness"] = target;
                            obj.InvokeMethod("WmiSetBrightness", inParams, null);
                        }
                    }
                }
            }
            catch { }
        }
    }
}
