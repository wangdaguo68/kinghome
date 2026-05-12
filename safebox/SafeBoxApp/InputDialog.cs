using System.Windows;
using Win = System.Windows;
using Controls = System.Windows.Controls;
using Media = System.Windows.Media;

namespace SafeBoxApp;

public sealed class InputDialog : Window
{
    public string? Result { get; private set; }

    public InputDialog(string title, string prompt, Window owner)
    {
        Owner = owner;
        Title = title;
        Width = 340;
        Height = 200;
        ResizeMode = ResizeMode.NoResize;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        WindowStyle = WindowStyle.None;
        AllowsTransparency = true;
        Background = Media.Brushes.Transparent;

        var mainBorder = new Controls.Border
        {
            Background = (Media.Brush)FindResource("BgElevated"),
            BorderBrush = (Media.Brush)FindResource("BorderAccent"),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(8),
            Margin = new Thickness(1)
        };

        var grid = new Controls.Grid();
        grid.RowDefinitions.Add(new Controls.RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new Controls.RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new Controls.RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new Controls.RowDefinition { Height = GridLength.Auto });
        grid.Margin = new Thickness(20);

        var titleBlock = new Controls.TextBlock
        {
            Text = prompt,
            Foreground = (Media.Brush)FindResource("TextPrimary"),
            FontSize = 13,
            Margin = new Thickness(0, 0, 0, 14)
        };
        Controls.Grid.SetRow(titleBlock, 0);
        grid.Children.Add(titleBlock);

        var textBox = new Controls.TextBox
        {
            Margin = new Thickness(0, 0, 0, 16)
        };
        Controls.Grid.SetRow(textBox, 1);
        grid.Children.Add(textBox);

        var buttons = new Controls.StackPanel { Orientation = Controls.Orientation.Horizontal, HorizontalAlignment = System.Windows.HorizontalAlignment.Right };
        var cancelBtn = new Controls.Button
        {
            Content = "取消",
            Style = (Style)FindResource("SecondaryButton"),
            Margin = new Thickness(0, 0, 8, 0)
        };
        cancelBtn.Click += (_, _) => { Result = null; DialogResult = false; Close(); };
        buttons.Children.Add(cancelBtn);

        var okBtn = new Controls.Button
        {
            Content = "创建",
            Style = (Style)FindResource("PrimaryButton")
        };
        okBtn.Click += (_, _) => { Result = textBox.Text.Trim(); DialogResult = true; Close(); };
        buttons.Children.Add(okBtn);

        Controls.Grid.SetRow(buttons, 2);
        grid.Children.Add(buttons);

        mainBorder.Child = grid;
        Content = mainBorder;
    }
}
